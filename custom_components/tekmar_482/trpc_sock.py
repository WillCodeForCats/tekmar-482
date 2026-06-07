import asyncio

from .trpc_msg import TrpcPacket


# ******************************************************************************
class TrpcSocket:
    # **************************************************************************
    def __init__(self, addr=None, port=None):
        self._sock_reader = None
        self._sock_writer = None
        self._is_open = False
        self._error = None
        self._rx_queue = []

        self.addr = addr
        self.port = port

    # **************************************************************************
    async def open(self) -> bool:
        """Connect to the socket.

        Return True if successful, False if not.
        """
        try:
            self._sock_reader, self._sock_writer = await asyncio.open_connection(
                self.addr, self.port
            )

            self._is_open = True
            return True

        except Exception as e:
            self._sock_reader = None
            self._sock_writer = None
            self._is_open = False
            self._error = e
            return False

    # **************************************************************************
    async def close(self) -> None:
        """Close the socket."""
        if self._sock_writer is not None:
            try:
                self._sock_writer.close()
                await self._sock_writer.wait_closed()

            except Exception:
                pass

            self._sock_writer = None
            self._sock_reader = None

            self._is_open = False

    # **************************************************************************
    async def read(self):
        """Read a packet from the socket.  If no packet is avaialble,
        None is returned.

        Otherwise a tHA object is returned.
        """
        if self._sock_reader is not None:
            if len(self._rx_queue) != 0:
                return self._rx_queue.pop(0)

            else:
                try:
                    rx_data = await asyncio.wait_for(
                        self._sock_reader.read(1024), timeout=0.5
                    )
                    rx_data = rx_data.rsplit("\n".encode())
                    for st in [r for r in rx_data if r]:
                        self._rx_queue.append(TrpcPacket.from_rx_packet(st))

                except asyncio.TimeoutError:
                    return None

        else:
            return None

    # **************************************************************************
    async def write(self, trpc_packet) -> None:
        """Write a TrpcPacket object to the socket."""
        if self._sock_writer is not None:
            self._sock_writer.write(str(trpc_packet.to_tpck()).encode())
            await self._sock_writer.drain()

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def error(self) -> str | None:
        return self._error
