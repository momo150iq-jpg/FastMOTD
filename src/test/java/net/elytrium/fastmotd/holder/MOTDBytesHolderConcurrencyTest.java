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

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.velocitypowered.api.network.ProtocolVersion;
import com.velocitypowered.api.proxy.server.ServerPing;
import com.velocitypowered.proxy.protocol.ProtocolUtils;
import io.netty.buffer.ByteBuf;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.FutureTask;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.locks.LockSupport;
import net.elytrium.fastmotd.utils.ByteBufCopyThreadLocal;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.minimessage.MiniMessage;
import org.junit.jupiter.api.Test;

class MOTDBytesHolderConcurrencyTest {

  @Test
  void onlineReplacementWaitsForRetainAndDoesNotChangeTheInFlightPacket() throws Exception {
    this.interleaved(false);
  }

  @Test
  void disposalWaitsForRetainAndLeavesTheSenderReferenceAlive() throws Exception {
    this.interleaved(true);
  }

  @Test
  void repeatedDisposalDoesNotReleaseTheSendersReference() {
    MOTDBytesHolder holder = newHolder();
    ByteBuf sending = holder.getByteBuf(ProtocolVersion.MINECRAFT_1_8, true);
    try {
      assertEquals(2, sending.refCnt());
      holder.dispose();
      assertEquals(1, sending.refCnt());
      holder.dispose();
      assertEquals(1, sending.refCnt());
      assertTrue(json(sending).contains("fixture"));
    } finally {
      holder.dispose();
      sending.release();
    }
    assertEquals(0, sending.refCnt());
  }

  private void interleaved(boolean dispose) throws Exception {
    MOTDBytesHolder holder = newHolder();
    Field sourceField = MOTDBytesHolder.class.getDeclaredField("byteBuf");
    sourceField.setAccessible(true);
    Field poolField = MOTDBytesHolder.class.getDeclaredField("localByteBuf");
    poolField.setAccessible(true);
    ByteBufCopyThreadLocal originalPool = (ByteBufCopyThreadLocal) poolField.get(holder);
    BlockingPool oldPool = new BlockingPool((ByteBuf) sourceField.get(holder));
    originalPool.release();
    poolField.set(holder, oldPool);

    AtomicReference<ByteBuf> sending = new AtomicReference<>();
    FutureTask<ByteBuf> read = new FutureTask<>(() -> {
      ByteBuf packet = holder.getByteBuf(ProtocolVersion.MINECRAFT_1_8, true);
      sending.set(packet);
      return packet;
    });
    Thread reader = worker("motd-ping", read);
    CountDownLatch mutationStarted = new CountDownLatch(1);
    FutureTask<Void> mutation = new FutureTask<>(() -> {
      mutationStarted.countDown();
      if (dispose) {
        holder.dispose();
      } else {
        holder.replaceOnline(300, 99);
      }
      return null;
    });
    Thread writer = worker("motd-replacement", mutation);

    try {
      reader.start();
      await(oldPool.acquired);
      writer.start();
      await(mutationStarted);
      awaitBlocked(writer);
      assertFalse(mutation.isDone(), "Pool destruction must wait until the reader owns its reference");

      oldPool.proceed.countDown();
      ByteBuf packet = read.get(5, TimeUnit.SECONDS);
      mutation.get(5, TimeUnit.SECONDS);
      assertEquals(1, packet.refCnt(), "Only the sender retains the old pool's buffer after replacement");
      assertTrue(json(packet).contains("\"online\":       1"));
      assertTrue(json(packet).contains("\"protocol\":       47"));

      if (!dispose) {
        ByteBuf current = holder.getByteBuf(ProtocolVersion.MINECRAFT_1_8, true);
        try {
          assertTrue(json(current).contains("\"online\":      99"));
          assertTrue(json(current).contains("\"max\":     300"));
        } finally {
          current.release();
        }
        ServerPing compat = holder.getCompatPingInfo(ProtocolVersion.MINECRAFT_1_8, true);
        assertEquals(99, compat.getPlayers().orElseThrow().getOnline());
        assertEquals(300, compat.getPlayers().orElseThrow().getMax());
      }
    } finally {
      oldPool.proceed.countDown();
      reader.join(5_000);
      writer.join(5_000);
      holder.dispose();
      ByteBuf packet = sending.get();
      if (packet != null) {
        packet.release();
        assertEquals(0, packet.refCnt(), "The sender's final release must free the old buffer");
      }
    }
  }

  private static MOTDBytesHolder newHolder() {
    return new MOTDBytesHolder(MiniMessage.miniMessage(), "{\"text\":\"fixture\"}",
        Component.text("fixture"), "test", null, List.of());
  }

  private static String json(ByteBuf sending) {
    ByteBuf packet = sending.duplicate();
    int frameLength = ProtocolUtils.readVarInt(packet);
    assertEquals(frameLength, packet.readableBytes());
    assertEquals(0, packet.readUnsignedByte());
    int jsonLength = ProtocolUtils.readVarInt(packet);
    assertEquals(jsonLength, packet.readableBytes());
    return packet.readCharSequence(jsonLength, StandardCharsets.UTF_8).toString();
  }

  private static Thread worker(String name, Runnable task) {
    Thread thread = new Thread(task, name);
    thread.setDaemon(true);
    return thread;
  }

  private static void await(CountDownLatch latch) throws InterruptedException {
    assertTrue(latch.await(5, TimeUnit.SECONDS), "The controlled interleaving did not reach its checkpoint");
  }

  private static void awaitBlocked(Thread thread) {
    long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5);
    while (thread.isAlive() && thread.getState() != Thread.State.BLOCKED && System.nanoTime() < deadline) {
      LockSupport.parkNanos(TimeUnit.MILLISECONDS.toNanos(1));
    }
    assertEquals(Thread.State.BLOCKED, thread.getState(), "Replacement must wait on the holder's acquisition lock");
  }

  private static final class BlockingPool extends ByteBufCopyThreadLocal {

    private final CountDownLatch acquired = new CountDownLatch(1);
    private final CountDownLatch proceed = new CountDownLatch(1);

    private BlockingPool(ByteBuf source) {
      super(source);
    }

    @Override
    public ByteBuf get() {
      ByteBuf packet = super.get();
      this.acquired.countDown();
      try {
        await(this.proceed);
      } catch (InterruptedException exception) {
        Thread.currentThread().interrupt();
        throw new AssertionError(exception);
      }
      return packet;
    }
  }
}
