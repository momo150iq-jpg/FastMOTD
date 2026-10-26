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

package net.elytrium.fastmotd.utils;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import net.kyori.adventure.key.Key;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.ObjectComponent;
import net.kyori.adventure.text.TextComponent;
import net.kyori.adventure.text.format.NamedTextColor;
import net.kyori.adventure.text.format.ShadowColor;
import net.kyori.adventure.text.minimessage.MiniMessage;
import net.kyori.adventure.text.minimessage.tag.Tag;
import net.kyori.adventure.text.minimessage.tag.resolver.TagResolver;
import net.kyori.adventure.text.object.ObjectContents;
import net.kyori.adventure.text.object.PlayerHeadObjectContents;
import net.kyori.adventure.text.object.SpriteObjectContents;

/**
 * Object components ({"type":"object"}) only exist since 1.21.9 (protocol 773),
 * and the separate "minecraft:items" atlas only since 1.21.11 (protocol 774).
 * These helpers downgrade a component tree for older clients.
 */
public final class ObjectComponents {

  public static final Key ITEMS_ATLAS = Key.key("minecraft", "items");

  private ObjectComponents() {
  }

  public enum Mode {
    /** Client renders object components and the items atlas (objects only get default color/shadow). */
    KEEP,
    /** 1.21.9 - 1.21.10: no items atlas, item/ sprites still live in the blocks atlas. */
    ITEMS_TO_BLOCKS,
    /** Before 1.21.9: object components are replaced with their fallback (or nothing). */
    STRIP
  }

  public static Component transform(Component component, Mode mode) {
    List<Component> children = new ArrayList<>(component.children().size());
    for (Component child : component.children()) {
      children.add(transform(child, mode));
    }

    if (component instanceof ObjectComponent object) {
      if (mode == Mode.STRIP) {
        TextComponent.Builder builder = Component.text().style(object.style());
        Component fallback = object.fallback();
        if (fallback != null) {
          builder.append(transform(fallback, mode));
        }

        return builder.append(children).build();
      }

      if (mode == Mode.ITEMS_TO_BLOCKS && object.contents() instanceof SpriteObjectContents sprite && ITEMS_ATLAS.equals(sprite.atlas())) {
        object = object.contents(ObjectContents.sprite(sprite.sprite()));
      }

      // Objects are drawn like glyphs: tinted by the text color and with a drop shadow. The server list draws
      // the MOTD in gray (0x808080) with shadow, so an object without its own color comes out half as bright
      // with a dark outline. Default them to untinted and shadowless.
      if (object.color() == null) {
        object = object.color(NamedTextColor.WHITE);
      }

      if (object.shadowColor() == null) {
        object = object.shadowColor(ShadowColor.shadowColor(0));
      }

      return object.children(children);
    }

    return component.children(children);
  }

  /**
   * MiniMessage with an extra {@code <head:Nick>} / {@code <head:uuid>} / {@code <head:Nick:false>} (no hat layer) tag.
   * Sprites already work out of the box: {@code <sprite:items:item/diamond_sword>}, {@code <sprite:gui:hud/heart/full>}.
   */
  public static MiniMessage miniMessage() {
    TagResolver head = TagResolver.resolver("head", (args, context) -> {
      String value = args.popOr("<head> needs a player name or UUID").value();
      PlayerHeadObjectContents.Builder builder = ObjectContents.playerHead();
      try {
        builder.id(UUID.fromString(value));
      } catch (IllegalArgumentException e) {
        builder.name(value);
      }

      if (args.hasNext()) {
        builder.hat(!"false".equalsIgnoreCase(args.pop().value()));
      }

      return Tag.selfClosingInserting(Component.object(builder.build()));
    });

    return MiniMessage.builder().editTags(tags -> tags.resolver(head)).build();
  }
}
