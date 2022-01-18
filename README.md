# tekmar-482
Home Assistant integration for the Tekmar 482 Gateway

Works with Add On Tekmar Packet Server:
https://github.com/WillCodeForCats/tekmar-packetserv

## Progress Updates
Please visit the wiki section. Documentation is being developed "on the fly" as the integration is developed. Once I have something that's relatively complete and tested, the first version of the integration will be made available on github and we'll see what happens with bug reports. I won't have hands on discontinued thermostats and snow melt controls (as much as I'd love a heated driveway to avoid shoveling snow, I don't have one) so these will probably rely on bug reports if I haven't interpreted the user manuals correctly.

https://github.com/WillCodeForCats/tekmar-482/wiki

Once I'm comfortable with my test platform I will connect it to my real home system and give it the "friends and family" test.

Jan 18, 2022: The Setpoint 161 control I ordered should be here by Friday.

Jan 8, 2022:

Purchased a Setpoint 161 and Thermostat 553 for additional testing (currently waiting for them to arrive).

* Added a User Swith 480 to my test platform for scene control.
* Initally tested and developed with a single Thermostat 557
* Outdoor tempeature is being provided by an sensor configured on the 577. On my real system, a 423 boiler control with the outdoor sensor.

Supports basic controls with the Home Assistant Climate entity:

<img width="401" alt="Screen Shot 2022-01-08 at 11 51 31 AM" src="https://user-images.githubusercontent.com/48533968/148657876-dcc1dddb-ddf3-40fd-91b7-4af45682efa5.png">

Additional controls will be exposed as other entity types, such as select for Fan Percent, switches for Setpoint or Snowmelt Enable/Disable, and useful sensors:

<img width="1119" alt="Screen Shot 2022-01-08 at 11 50 10 AM" src="https://user-images.githubusercontent.com/48533968/148657815-16713767-5a05-4201-b884-843376bba374.png">
