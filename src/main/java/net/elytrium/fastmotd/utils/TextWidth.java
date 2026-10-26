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

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.util.Objects;
import net.kyori.adventure.key.Key;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.ObjectComponent;
import net.kyori.adventure.text.TextComponent;
import net.kyori.adventure.text.format.Style;
import net.kyori.adventure.text.format.TextDecoration;

/**
 * Vanilla text width, from glyph advances of the 26.x default font (fastmotd/glyph-widths.bin, built by box/gen_widths.py).
 * The table has two 65536-entry parts (minecraft:default, minecraft:uniform): advance in half pixels,
 * high bit = unihex glyph (bold adds 0.5 px instead of 1 px), 0 = missing glyph (6 px box).
 */
public final class TextWidth {

  /** Server list: row 305, content 301, MOTD split at content width - 32 - 2. */
  public static final int MOTD_WIDTH = 267;

  private static final Key UNIFORM = Key.key("minecraft", "uniform");
  private static final int SPRITE_ADVANCE = 8;
  private static final byte[] TABLE = load();

  private TextWidth() {
  }

  private static byte[] load() {
    try (InputStream in = Objects.requireNonNull(TextWidth.class.getResourceAsStream("/fastmotd/glyph-widths.bin"))) {
      return in.readAllBytes();
    } catch (IOException e) {
      throw new UncheckedIOException(e);
    }
  }

  /** Width in pixels, rounded up like the client does. */
  public static int width(Component component) {
    return (halfWidth(component, false, null) + 1) / 2;
  }

  private static int halfWidth(Component component, boolean bold, Key font) {
    Style style = component.style();
    TextDecoration.State state = style.decoration(TextDecoration.BOLD);
    if (state != TextDecoration.State.NOT_SET) {
      bold = state == TextDecoration.State.TRUE;
    }

    if (style.font() != null) {
      font = style.font();
    }

    int width = 0;
    if (component instanceof TextComponent text) {
      width += textHalfWidth(text.content(), bold, UNIFORM.equals(font));
    } else if (component instanceof ObjectComponent) {
      width += SPRITE_ADVANCE * 2 + (bold ? 2 : 0);
    }

    for (Component child : component.children()) {
      width += halfWidth(child, bold, font);
    }

    return width;
  }

  private static int textHalfWidth(String text, boolean bold, boolean uniform) {
    int width = 0;
    int offset = uniform ? 65536 : 0;
    for (int i = 0; i < text.length(); ) {
      int codePoint = text.codePointAt(i);
      i += Character.charCount(codePoint);
      int value = codePoint <= 0xFFFF ? TABLE[offset + codePoint] & 0xFF : 0;
      if (value == 0) {
        width += 12 + (bold ? 2 : 0);
      } else {
        width += (value & 0x7F) + (bold ? ((value & 0x80) != 0 ? 1 : 2) : 0);
      }
    }

    return width;
  }

  /**
   * Left padding that centers a line of the given width: regular spaces (4 px) plus bold spaces (5 px).
   */
  public static Component centerPadding(int lineWidth) {
    int pad = (MOTD_WIDTH - lineWidth) / 2;
    for (; pad >= 4; pad--) {
      for (int bold = 0; bold <= 3 && bold * 5 <= pad; bold++) {
        if ((pad - bold * 5) % 4 == 0) {
          return Component.text()
              .append(Component.text(" ".repeat((pad - bold * 5) / 4)).decoration(TextDecoration.BOLD, false))
              .append(Component.text(" ".repeat(bold)).decoration(TextDecoration.BOLD, true))
              .build();
        }
      }
    }

    return Component.empty();
  }
}
