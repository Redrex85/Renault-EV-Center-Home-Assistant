# Renault EV Center — Review

Date: 2026-09-06  
Scope: `custom_components/renault_ev_center`, dashboards, docs, HACS readiness.

## Verdetto

Not publish-ready yet. Feature set is broad, but there are blocking `NameError` bugs and several automation/settings paths that do not work as the UI promises.

Priority:

1. Fix missing imports.
2. Wire dashboard `number`/`switch` entities into coordinator logic.
3. Fix scheduled charge and early-exit behavior.
4. Re-test on HA before HACS/GitHub release.

---

## P0 — Blocking

### 1. `coordinator.py` uses `DOMAIN` without importing it

Evidence:

- `custom_components/renault_ev_center/coordinator.py:19` imports from `.const`, but does not include `DOMAIN`.
- `custom_components/renault_ev_center/coordinator.py:268` uses `DOMAIN`.
- `custom_components/renault_ev_center/coordinator.py:278` uses `DOMAIN`.
- `custom_components/renault_ev_center/const.py:4` defines `DOMAIN`.

Impact:

- `NameError` during coordinator construction or device-info generation.
- Integration can fail to load.

Minimal fix:

```python
from .const import (
    DOMAIN,
    ...
)
```

Add `DOMAIN` to the existing `.const` import block in `coordinator.py`.

---

### 2. `coordinator.py` uses `CONF_WB_MAX_CURRENT` without importing it

Evidence:

- `custom_components/renault_ev_center/coordinator.py:19` imports from `.const`, but does not include `CONF_WB_MAX_CURRENT`.
- `custom_components/renault_ev_center/coordinator.py:1511` uses `CONF_WB_MAX_CURRENT`.
- `custom_components/renault_ev_center/const.py:22` defines `CONF_WB_MAX_CURRENT`.

Impact:

- `NameError` when solar balancing runs.
- Solar balancing is effectively broken.

Minimal fix:

```python
from .const import (
    CONF_WB_MAX_CURRENT,
    DOMAIN,
    ...
)
```

---

### 3. `config_flow.py` uses maintenance/notification constants without importing them

Evidence:

- `custom_components/renault_ev_center/config_flow.py:23` imports from `.const`.
- Missing imported constants:
  - `CONF_NOTIFY_SERVICE`
  - `CONF_NOTIFY_DAYS`
  - `CONF_TAGLIANDO_MODE`
  - `CONF_TAGLIANDO_DATA`
  - `CONF_ASSICURAZIONE_COSTO`
  - `CONF_ASSICURAZIONE_DATA`
  - `CONF_NOTIFY_CHARGE_START`
  - `CONF_NOTIFY_CHARGE_END`
- Used at:
  - `custom_components/renault_ev_center/config_flow.py:212`
  - `custom_components/renault_ev_center/config_flow.py:213`
  - `custom_components/renault_ev_center/config_flow.py:215`
  - `custom_components/renault_ev_center/config_flow.py:217`
  - `custom_components/renault_ev_center/config_flow.py:218`
  - `custom_components/renault_ev_center/config_flow.py:220`
  - `custom_components/renault_ev_center/config_flow.py:221`
  - `custom_components/renault_ev_center/config_flow.py:222`
  - `custom_components/renault_ev_center/config_flow.py:340`
  - `custom_components/renault_ev_center/config_flow.py:341`
  - `custom_components/renault_ev_center/config_flow.py:342`
  - `custom_components/renault_ev_center/config_flow.py:343`
  - `custom_components/renault_ev_center/config_flow.py:344`
  - `custom_components/renault_ev_center/config_flow.py:345`
- Defined at:
  - `custom_components/renault_ev_center/const.py:54`
  - `custom_components/renault_ev_center/const.py:55`
  - `custom_components/renault_ev_center/const.py:56`
  - `custom_components/renault_ev_center/const.py:57`
  - `custom_components/renault_ev_center/const.py:58`
  - `custom_components/renault_ev_center/const.py:59`
  - `custom_components/renault_ev_center/const.py:69`
  - `custom_components/renault_ev_center/const.py:70`

Impact:

- `NameError` while building the settings/options schema.
- Config flow wizard can be unusable.

Minimal fix:

```python
from .const import (
    CONF_ASSICURAZIONE_COSTO,
    CONF_ASSICURAZIONE_DATA,
    CONF_NOTIFY_CHARGE_END,
    CONF_NOTIFY_CHARGE_START,
    CONF_NOTIFY_DAYS,
    CONF_NOTIFY_SERVICE,
    CONF_TAGLIANDO_DATA,
    CONF_TAGLIANDO_MODE,
    ...
)
```

---

## P1 — Functional bugs

### 4. Dashboard `number` entities are created, but most are not wired into calculations

Evidence:

- `number.py` creates editable entities:
  - `custom_components/renault_ev_center/number.py:36` `price_home`
  - `custom_components/renault_ev_center/number.py:38` `price_public`
  - `custom_components/renault_ev_center/number.py:40` `price_solar`
  - `custom_components/renault_ev_center/number.py:42` `capacity`
  - `custom_components/renault_ev_center/number.py:44` `target`
  - `custom_components/renault_ev_center/number.py:46` `soh_official`
  - `custom_components/renault_ev_center/number.py:48` `assic_costo`
  - `custom_components/renault_ev_center/number.py:50` `low_soc`
  - `custom_components/renault_ev_center/number.py:52` `charge_start_soc`
  - `custom_components/renault_ev_center/number.py:54` `charge_stop_soc`
  - `custom_components/renault_ev_center/number.py:56` `balance_min_amps`
  - `custom_components/renault_ev_center/number.py:58` `balance_max_amps`
  - `custom_components/renault_ev_center/number.py:60` `battery_priority`
- Coordinator reads only some number entities:
  - `custom_components/renault_ev_center/coordinator.py:793` `soh_official`
  - `custom_components/renault_ev_center/coordinator.py:1074` `soh_official`
  - `custom_components/renault_ev_center/coordinator.py:1532` `battery_priority`
  - `custom_components/renault_ev_center/coordinator.py:1541` `balance_min_amps`
  - `custom_components/renault_ev_center/coordinator.py:1542` `balance_max_amps`
  - `custom_components/renault_ev_center/coordinator.py:1596` `low_soc`
  - `custom_components/renault_ev_center/coordinator.py:1628` `charge_start_soc`
  - `custom_components/renault_ev_center/coordinator.py:1629` `charge_stop_soc`
- Prices, capacity, target SoC, and insurance cost are still read from config options:
  - `custom_components/renault_ev_center/coordinator.py:163`
  - `custom_components/renault_ev_center/coordinator.py:164`
  - `custom_components/renault_ev_center/coordinator.py:165`
  - `custom_components/renault_ev_center/coordinator.py:166`
  - `custom_components/renault_ev_center/coordinator.py:167`
  - `custom_components/renault_ev_center/coordinator.py:193`
- Dashboards expose those number entities to users:
  - `custom_components/renault_ev_center/dashboards/06_impostazioni.yaml:21`
  - `custom_components/renault_ev_center/dashboards/06_impostazioni.yaml:22`
  - `custom_components/renault_ev_center/dashboards/06_impostazioni.yaml:31`
  - `custom_components/renault_ev_center/dashboards/06_impostazioni.yaml:32`
  - `custom_components/renault_ev_center/dashboards/05_salute_batteria.yaml:49`
  - `custom_components/renault_ev_center/dashboards/12_gestione.yaml:35`

Impact:

- User edits price/capacity/target/insurance in dashboard.
- Coordinator continues using old config-option values.
- UI is misleading.

Minimal fix:

Add a helper in `coordinator.py`:

```python
def _apply_number_settings(self) -> None:
    self.capacity = self._setting_num("capacity", self._cfg_capacity) or self._cfg_capacity
    self.target_soc = self._setting_num("target", self._cfg_target_soc)
    self.price_home = self._setting_num("price_home", self._cfg_price_home)
    self.price_public = self._setting_num("price_public", self._cfg_price_public)
    self.price_solar = self._setting_num("price_solar", self._cfg_price_solar)
    self.assicurazione_costo = self._setting_num("assic_costo", self.assicurazione_costo)
    self.trip.capacity_kwh = self.capacity
```

Call it near the start of `_async_update_data_inner()`, before early-exit:

```python
self._apply_number_settings()
```

This keeps config options as fallback and makes dashboard numbers authoritative after setup.

---

### 5. Early-exit skips automation logic and setting changes

Evidence:

- `custom_components/renault_ev_center/coordinator.py:528`
- `custom_components/renault_ev_center/coordinator.py:529`
- `custom_components/renault_ev_center/coordinator.py:530`
- `custom_components/renault_ev_center/coordinator.py:531`

Current behavior:

```python
_curr_inputs = (round(odometer, 2), round(battery, 1), charging, wb_state, location, self._wb_counter())
if self._last_inputs == _curr_inputs and not self.trip.active and not self.charge_session and self.data:
    return self.data
```

Impact:

- If car state is unchanged, coordinator returns cached data.
- Scheduled charge may not run.
- Solar balancing may not run.
- Low SoC reminders may not run.
- Number/switch/time/select changes may not take effect until a car/wallbox value changes.

Minimal fix:

Include automation settings in the early-exit signature, or skip early-exit when automations are enabled.

Example:

```python
settings_sig = (
    self.capacity,
    self.target_soc,
    self.price_home,
    self.price_public,
    self.price_solar,
    self.assicurazione_costo,
    self._switch_on("balance"),
    self._switch_on("charge_sched"),
    self._switch_on("low_soc"),
    self._switch_on("notify_start"),
    self._switch_on("notify_end"),
    self._setting_time("charge_start_time", self.charge_start_time),
    self._setting_time("charge_stop_time", self.charge_stop_time),
    self._setting_time("low_soc_start", self.low_soc_start),
    self._setting_time("low_soc_end", self.low_soc_end),
)

_curr_inputs = (
    round(odometer, 2),
    round(battery, 1),
    charging,
    wb_state,
    location,
    self._wb_counter(),
    settings_sig,
)
```

Also make `switch.py` request refresh on toggle:

```python
async def async_turn_on(self, **kwargs) -> None:
    self._attr_is_on = True
    self.async_write_ha_state()
    await self.coordinator.async_request_refresh()

async def async_turn_off(self, **kwargs) -> None:
    self._attr_is_on = False
    self.async_write_ha_state()
    await self.coordinator.async_request_refresh()
```

---

### 6. Scheduled charge overnight window is broken

Evidence:

- `custom_components/renault_ev_center/coordinator.py:1626`
- `custom_components/renault_ev_center/coordinator.py:1627`
- `custom_components/renault_ev_center/coordinator.py:1631`
- `custom_components/renault_ev_center/coordinator.py:1632`
- `custom_components/renault_ev_center/coordinator.py:1633`
- `custom_components/renault_ev_center/coordinator.py:1634`
- `custom_components/renault_ev_center/coordinator.py:1637`
- `custom_components/renault_ev_center/coordinator.py:1638`
- `custom_components/renault_ev_center/coordinator.py:1642`

Problem:

Default window is start `23:30`, stop `07:00`.

Current logic uses direct string comparisons:

```python
avvia_ora = hhmm >= avvio_ora_s
ferma_ora = hhmm >= self.charge_stop_time and hhmm < self.charge_start_time or (
    self.charge_stop_time <= hhmm < self.charge_start_time
)
```

Issues:

- `ferma_ora` is calculated but not used.
- Start condition requires `hhmm < stop_ora_s`.
- At `23:30`, `23:30 < 07:00` is false, so scheduled charge does not start.
- Stop condition also mixes selected time entities with raw config values.

Minimal fix:

Add a helper:

```python
def _in_window(hhmm: str, start: str, stop: str) -> bool:
    if start <= stop:
        return start <= hhmm < stop
    return hhmm >= start or hhmm < stop
```

Then use:

```python
in_window = _in_window(hhmm, avvio_ora_s, stop_ora_s)

if not charging and in_window and self._sched_done_key != f"start_{today_key}":
    await self._wb_charge(True, battery)
    self._sched_done_key = f"start_{today_key}"

if charging and not in_window:
    await self._wb_charge(False, battery)
```

This supports overnight windows like `23:30` to `07:00`.

---

### 7. `balance_max_amps` initial value reads a non-existent config key

Evidence:

- `custom_components/renault_ev_center/number.py:59` uses `base.get("wb_max_amps", 16.0)`.
- `custom_components/renault_ev_center/const.py:22` defines `CONF_WB_MAX_CURRENT = "wallbox_max_current_entity"`.
- `custom_components/renault_ev_center/config_flow.py:167` stores an entity ID under `CONF_WB_MAX_CURRENT`.
- `custom_components/renault_ev_center/coordinator.py:1511` reads that entity ID.
- `custom_components/renault_ev_center/coordinator.py:1542` reads `balance_max_amps` as amps.

Impact:

- Initial max amps almost always falls back to `16.0`.
- Not fatal, but config intent is unclear.

Minimal fix:

Either:

```python
float(base.get("balance_max_amps", 16.0))
```

or add a real config option for max amps. Do not use `wb_max_amps` unless that key is added to config flow and const.

---

## P2 — Risks and polish

### 8. Broad update exception can hide persistent failures

Evidence:

- `custom_components/renault_ev_center/coordinator.py:499`
- `custom_components/renault_ev_center/coordinator.py:500`
- `custom_components/renault_ev_center/coordinator.py:501`
- `custom_components/renault_ev_center/coordinator.py:502`
- `custom_components/renault_ev_center/coordinator.py:503`
- `custom_components/renault_ev_center/coordinator.py:504`
- `custom_components/renault_ev_center/coordinator.py:505`

Impact:

- Persistent errors can look like stale but working data.
- Harder for users to diagnose broken entity mappings.

Recommendation:

Keep fallback for transient errors, but consider raising `UpdateFailed` after repeated failures or logging at a higher severity after N consecutive failures.

Minimal version:

```python
self._update_failures = getattr(self, "_update_failures", 0) + 1
if self._update_failures >= 5:
    raise
```

Reset counter on success.

---

### 9. Notify service may not support `title`

Evidence:

- `custom_components/renault_ev_center/coordinator.py:1444`
- `custom_components/renault_ev_center/coordinator.py:1450`
- `custom_components/renault_ev_center/coordinator.py:1451`

Impact:

- Some notify integrations accept only `message`.
- Notifications may fail silently or log warnings.

Recommendation:

Catch service errors and retry with message-only payload, or document that `notify` target must support title.

Minimal fallback:

```python
try:
    await self.hass.services.async_call(
        "notify", service, {"title": title, "message": message}, blocking=False,
    )
except Exception:
    await self.hass.services.async_call(
        "notify", service, {"message": f"{title}\n{message}"}, blocking=False,
    )
```

---

### 10. Duplicate imports in `coordinator.py`

Evidence:

- `custom_components/renault_ev_center/coordinator.py:37` imports `CONF_NOTIFY_DAYS`.
- `custom_components/renault_ev_center/coordinator.py:83` imports `CONF_NOTIFY_DAYS` again.
- `custom_components/renault_ev_center/coordinator.py:38` imports `CONF_NOTIFY_SERVICE`.
- `custom_components/renault_ev_center/coordinator.py:84` imports `CONF_NOTIFY_SERVICE` again.

Impact:

- No runtime bug.
- Lint noise.

Fix:

Remove duplicates.

---

### 11. `number.py` uses raw string keys where constants exist

Evidence:

- `custom_components/renault_ev_center/number.py:49` uses `"assicurazione_costo"`.
- `custom_components/renault_ev_center/number.py:51` uses `"low_soc_threshold"`.
- `custom_components/renault_ev_center/number.py:53` uses `"charge_start_soc"`.
- `custom_components/renault_ev_center/number.py:55` uses `"charge_stop_soc"`.
- `custom_components/renault_ev_center/number.py:59` uses `"wb_max_amps"`.

Impact:

- Minor maintenance risk.
- One of these is already a real bug: `wb_max_amps`.

Fix:

Use constants where they exist.

---

## HACS / GitHub readiness

Before publishing:

1. Fix all P0 import errors.
2. Fix P1 number wiring and scheduled charge.
3. Reload integration in HA and check logs for `NameError`.
4. Test config flow:
   - new entry,
   - options flow,
   - maintenance settings,
   - charge settings,
   - solar settings.
5. Test runtime:
   - scheduled charge overnight window,
   - solar balancing,
   - low SoC reminder,
   - dashboard number edits affecting sensors.
6. Replace README donation placeholders:
   - `paypal.me/TUO-NOME`
   - `buymeacoffee.com/TUO-NOME`
7. Keep `manifest.json` version aligned with git tag.

---

## Recommended patch order

### Patch 1 — imports

Files:

- `custom_components/renault_ev_center/coordinator.py`
- `custom_components/renault_ev_center/config_flow.py`

Goal:

- Remove all `NameError` blockers.

### Patch 2 — number wiring

Files:

- `custom_components/renault_ev_center/coordinator.py`

Goal:

- Dashboard numbers become live settings.

### Patch 3 — early-exit and switch refresh

Files:

- `custom_components/renault_ev_center/coordinator.py`
- `custom_components/renault_ev_center/switch.py`

Goal:

- Automation changes take effect immediately.

### Patch 4 — scheduled charge window

Files:

- `custom_components/renault_ev_center/coordinator.py`

Goal:

- `23:30` to `07:00` works.

### Patch 5 — minor polish

Files:

- `custom_components/renault_ev_center/coordinator.py`
- `custom_components/renault_ev_center/number.py`

Goal:

- Remove duplicate imports, fix `balance_max_amps` initial key, improve notify fallback.

---

## Validation commands

From project root:

```powershell
& "C:\Users\Redrex\AppData\Local\Programs\Python\Launcher\py.exe" -m py_compile (Get-ChildItem -Recurse -Filter *.py | ForEach-Object { $_.FullName })
```

Run existing status checker:

```powershell
& "C:\Users\Redrex\AppData\Local\Programs\Python\Launcher\py.exe" tools\check_status.py
```

After fixes, reload/restart HA and check logs for:

```text
NameError
Update fallito
Bilanciamento
Carica programmata
Notifica fallita
```

---

## Final recommendation

Do not publish to HACS yet.

The integration is feature-rich, but the current code can fail during setup/options flow and the advertised dashboard controls are not fully connected. Fix the P0/P1 items first; after that, the project is close to release quality.

---

## Applied in this pass

Patches applied after this review:

- Added missing `DOMAIN` and `CONF_WB_MAX_CURRENT` imports in `coordinator.py`.
- Added missing maintenance/notification constants in `config_flow.py`.
- Removed duplicate `CONF_NOTIFY_DAYS` and `CONF_NOTIFY_SERVICE` imports in `coordinator.py`.
- Added `_apply_number_settings()` so dashboard numbers for capacity, target, prices, and insurance feed coordinator calculations.
- Added `_automation_sig()` and included it in the early-exit check so number/switch/time/select changes are not skipped.
- Fixed scheduled charge overnight windows with `_in_window()`.
- Made `switch.py` request a coordinator refresh on toggle.
- Fixed `number.py` initial `balance_max_amps` key from non-existent `wb_max_amps` to `balance_max_amps`.

Validation after patch:

```powershell
& "C:\Users\Redrex\AppData\Local\Programs\Python\Launcher\py.exe" -m compileall -q custom_components
& "C:\Users\Redrex\AppData\Local\Programs\Python\Launcher\py.exe" tools\check_status.py
```

Result:

- `compileall`: passed.
- `tools/check_status.py`: 84 checks passed.

Remaining before HACS:

1. Reload/restart HA and confirm no `NameError` in logs.
2. Test config flow and options flow.
3. Test scheduled charge with `23:30` to `07:00`.
4. Test solar balancing with wallbox current entity mapped.
5. Test dashboard number edits affecting sensors.
