# FastMOTD box-motd (BomjPVP fork)

MOTD tiers by client protocol (main.tiers in config.yml, first match wins, "off" disables a tier):

- 773+ (1.21.9+): object components - <sprite:items:item/diamond_sword>, <sprite:gui:hud/heart/full>, <sprite:block/tnt_side>, <head:Nick>
- 769-772 (1.21.4-1.21.8): gradients, <shadow:#rrggbb:alpha>, vanilla fonts (<font:uniform>, alt, illageralt)
- below: normal MOTD from main.descriptions / main.versions

Per client the status JSON is serialized with the matching Velocity serializer; object components are
dropped (fallback kept) below 773, and the minecraft:items atlas is rewritten to the blocks atlas for 773
(the items atlas only exists since 1.21.11 / 774). Only vanilla atlases and fonts render in the server list.

Build against the live proxy jar (compiled for Java 25):

    ./gradlew build -PvelocityJar=/home/bomj/proxy/velocity-4.2.1-SNAPSHOT-32.jar -PcompilerVersion=25       -Porg.gradle.java.installations.paths=/home/java/jdk-25.0.4.1+1 -Porg.gradle.java.installations.auto-download=false

Check: python3 box/ping.py 127.0.0.1 25599 775,774,773,772,769,767,47
