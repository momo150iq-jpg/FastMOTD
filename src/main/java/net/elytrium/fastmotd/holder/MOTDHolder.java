/*
 * Copyright (C) 2022 - 2025 Elytrium
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

package net.elytrium.fastmotd.holder;

import com.velocitypowered.api.network.ProtocolVersion;
import com.velocitypowered.api.proxy.server.ServerPing;
import com.velocitypowered.proxy.protocol.ProtocolUtils;
import io.netty.buffer.ByteBuf;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import net.elytrium.fastmotd.utils.ObjectComponents;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.serializer.ComponentSerializer;
import net.kyori.adventure.text.serializer.gson.GsonComponentSerializer;

public class MOTDHolder {

  // Lowest protocol of each render profile, newest first. Each profile gets its own JSON serializer
  // and object component handling, identical outputs share one prepared buffer.
  private static final ProtocolVersion[] PROFILES = {
      ProtocolVersion.MINECRAFT_1_21_11,
      ProtocolVersion.MINECRAFT_1_21_9,
      ProtocolVersion.MINECRAFT_1_21_5,
      ProtocolVersion.MINECRAFT_1_20_3,
      ProtocolVersion.MINECRAFT_1_16,
      ProtocolVersion.MINIMUM_VERSION
  };

  private final MOTDBytesHolder[] holders = new MOTDBytesHolder[PROFILES.length];
  private final List<MOTDBytesHolder> distinctHolders;

  public MOTDHolder(ComponentSerializer<Component, Component, String> serializer, String versionName,
                    String descriptionSerialized, String favicon, List<String> information) {
    String name = versionName.replace("\"", "\\\"");
    Component description = serializer.deserialize(descriptionSerialized.replace("{NL}", "\n"));

    Map<String, MOTDBytesHolder> unique = new HashMap<>();
    for (int i = 0; i < PROFILES.length; i++) {
      ProtocolVersion profile = PROFILES[i];
      Component transformed = ObjectComponents.transform(description, objectMode(profile));
      GsonComponentSerializer outputSerializer = ProtocolUtils.getJsonChatSerializer(profile);
      String json = outputSerializer.serialize(transformed);
      this.holders[i] = unique.computeIfAbsent(json, j -> new MOTDBytesHolder(serializer, j, transformed, name, favicon, information));
    }

    this.distinctHolders = List.copyOf(unique.values());
  }

  private static ObjectComponents.Mode objectMode(ProtocolVersion version) {
    if (version.noLessThan(ProtocolVersion.MINECRAFT_1_21_11)) {
      return ObjectComponents.Mode.KEEP;
    } else if (version.noLessThan(ProtocolVersion.MINECRAFT_1_21_9)) {
      return ObjectComponents.Mode.ITEMS_TO_BLOCKS;
    } else {
      return ObjectComponents.Mode.STRIP;
    }
  }

  private MOTDBytesHolder holder(ProtocolVersion version) {
    for (int i = 0; i < PROFILES.length; i++) {
      if (version.noLessThan(PROFILES[i])) {
        return this.holders[i];
      }
    }

    return this.holders[PROFILES.length - 1];
  }

  public void replaceOnline(int max, int online) {
    for (MOTDBytesHolder holder : this.distinctHolders) {
      holder.replaceOnline(max, online);
    }
  }

  public ByteBuf getByteBuf(ProtocolVersion version, boolean replaceProtocol) {
    return this.holder(version).getByteBuf(version, replaceProtocol);
  }

  public ServerPing getCompatPingInfo(ProtocolVersion version, boolean replaceProtocol) {
    return this.holder(version).getCompatPingInfo(version, replaceProtocol);
  }

  public void dispose() {
    for (MOTDBytesHolder holder : this.distinctHolders) {
      holder.dispose();
    }
  }
}
