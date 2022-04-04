
def regBytes(integer):
    return divmod(integer, 0x100)

def degCtoF(degC):
    """ convert Celcius to degF """
    return ((degC * 9/5) + 32)

def degEtoC(degE):
    """ convert degE to degC """
    #degE = 2*(degC)
    return (degE / 2)

def degHtoF(degH):
    """ convert degH to degF """
    #degH = 10*(degF) + 850
    return ((degH - 850) / 10)

def degFtoC(degF):
    """ convert degF to degC """
    #degC = (degF - 32) / 1.8
    return ((degF - 32) / 1.8)
    
def degHtoC(degH):
    return degFtoC(degHtoF(degH))
