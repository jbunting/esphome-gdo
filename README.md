# esphome-gdo

An [ESPHome](https://esphome.io) external component for Chamberlain / LiftMaster
**Security+ 1.0 and 2.0** garage door openers, built on top of
[gdolib](https://github.com/jbunting/gdolib) (multi-instance fork).

Because gdolib is now multi-instance, this component supports **multiple openers
on one board** — declare one `secplus_gdo` hub per UART port.

## Requirements

- An ESP32 (the component pulls in gdolib as an ESP-IDF component).
- The **esp-idf** framework (`esp32: framework: type: esp-idf`). The component
  fails validation on the Arduino framework.
- A wiring interface to the opener's Security+ wall-panel bus (e.g. a Konnected
  blaQ or an equivalent level-shifter). If your interface inverts the UART, set
  `invert_uart: true`.

## Installation

```yaml
external_components:
  - source: github://jbunting/esphome-gdo
    components: [secplus_gdo]
```

The component declares its own dependency on gdolib, so you don't need to add it
to `lib_deps` yourself.

## Hub configuration (`secplus_gdo:`)

`secplus_gdo` is a hub component (`MULTI_CONF`) — list one per opener.

```yaml
secplus_gdo:
  - id: gdo_main
    tx_pin: 17
    rx_pin: 16
```

| Option | Type | Default | Description |
|---|---|---|---|
| `id` | id | — | Hub id, referenced by the entity platforms. |
| `tx_pin` | pin | **required** | GPIO wired to the opener bus (UART TX). |
| `rx_pin` | pin | **required** | GPIO wired to the opener bus (UART RX). |
| `obstruction_pin` | pin | — | Optional discrete obstruction-sensor input. |
| `obstruction_from_status` | bool | `true` | Derive obstruction from Sec+ 2.0 status frames instead of a pin. |
| `invert_uart` | bool | `false` | Invert the UART signal (set `true` for inverting interfaces). |
| `uart_num` | 0–2 | auto | UART port. Omit to auto-assign starting at UART1 (UART0 is the console). |

## Entities

Each entity references its hub via `secplus_gdo_id` (optional when there is only
one hub).

```yaml
cover:
  - platform: secplus_gdo
    secplus_gdo_id: gdo_main
    name: Garage Door
    device_class: garage

light:
  - platform: secplus_gdo
    secplus_gdo_id: gdo_main
    name: Garage Light

lock:
  - platform: secplus_gdo
    secplus_gdo_id: gdo_main
    name: Garage Lock
```

The cover supports open/close/stop/toggle and position (move-to-target).
gdolib handles Security+ v1 vs v2 auto-detection, the toggle-only /
stop-then-toggle behavior, and rolling-code management; the hub persists the
Security+ 2.0 credentials (client id + rolling code) to flash so the opener
keeps accepting commands across reboots.

### Read-only sensors

```yaml
binary_sensor:
  - platform: secplus_gdo
    secplus_gdo_id: gdo_main
    type: motion          # motion | obstruction | motor | button
    name: Garage Motion

sensor:
  - platform: secplus_gdo
    secplus_gdo_id: gdo_main
    type: openings        # openings | time_to_close
    name: Garage Openings
```

### Controls and settings

```yaml
switch:
  - platform: secplus_gdo
    type: learn           # learn | toggle_only
    name: Garage Learn

select:
  - platform: secplus_gdo
    name: Garage Protocol   # auto / secplus_v1 / secplus_v2 / secplus_v1_with_smart_panel
    initial_option: auto

number:
  - platform: secplus_gdo
    type: open_duration   # open_duration | close_duration | client_id | rolling_code
    name: Garage Open Duration
    unit_of_measurement: ms
```

Notes:
- `open_duration` / `close_duration` (ms) are measured automatically the first
  time the door makes a full run, and are needed for `move-to-target` position
  control. They persist and are restored into the opener on boot.
- `toggle_only` forces the single-button behavior for openers without a status
  line; it persists across reboots.
- `select` (protocol) restores the saved protocol on boot to skip
  auto-detection; changing it after startup reboots to apply cleanly.
- `client_id` / `rolling_code` numbers are for visibility and advanced
  pre-sync override. They display as floats, so very large rolling-code values
  lose precision — the exact values are persisted by the hub, not the number.

## Multiple openers

Give each hub its own UART port and pins:

```yaml
secplus_gdo:
  - id: gdo_left
    tx_pin: 17
    rx_pin: 16
  - id: gdo_right
    tx_pin: 19
    rx_pin: 18

cover:
  - platform: secplus_gdo
    secplus_gdo_id: gdo_left
    name: Left Door
  - platform: secplus_gdo
    secplus_gdo_id: gdo_right
    name: Right Door
```

ESP32 variants expose 1–3 hardware UARTs; UART0 is normally the logger console,
so a classic ESP32 can drive up to two openers alongside logging (or three if
you free UART0).

See [`example.yaml`](example.yaml) for a complete two-opener configuration.

## Status

All entities are implemented: cover, light, lock, `binary_sensor` (motion /
obstruction / motor / button), `sensor` (openings / time-to-close),
`switch` (learn / toggle-only), `select` (protocol), and `number`
(open/close duration, client id, rolling code). The full `example.yaml`
compiles under ESPHome 2026.6.

## License

GPL-3.0-or-later — see [LICENSE](LICENSE). This component builds on and is
derived from [gdolib](https://github.com/jbunting/gdolib) and
[konnected-io/konnected-esphome](https://github.com/konnected-io/konnected-esphome),
both GPL-3.0-or-later.
