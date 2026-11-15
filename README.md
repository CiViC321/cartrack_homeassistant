# CarTrack for Home Assistant

Connect a CarTrack Fleet account to Home Assistant and monitor its vehicles. This is a cloud-polling integration: vehicle data is retrieved from the CarTrack Fleet API, not directly from the vehicle.

Requires Home Assistant 2024.4.0 or newer.

## Install with HACS

In HACS, open **Integrations**, choose **Custom repositories** from the menu, and add this repository's URL with the **Integration** category. Find **CarTrack** in HACS and download it, then restart Home Assistant.

Alternatively, manually copy `custom_components/cartrack` into the Home Assistant configuration directory under `custom_components/cartrack`, then restart Home Assistant.

## Set Up

In Home Assistant, go to **Settings → Devices & services → Add integration → CarTrack**. Enter your CarTrack username and API key, then select the region for your account. The selected region determines the Fleet API URL; see CarTrack's [Fleet API base URL documentation](https://developer.cartrack.com/docs/fleet-api-general/base-url). The integration checks the credentials by requesting vehicle data during setup.

Add the integration separately for each CarTrack account. Each account is polled independently. The same account and region cannot be added twice.

## What It Adds

The integration creates a Home Assistant device for each vehicle reported by CarTrack. It also adds devices and entities when new vehicles appear in the account.

| Entity | Behavior |
| --- | --- |
| **Status** | Reports **Parked**, **Idling**, **Driving**, or **Ignition on**, based on the ignition, idling, and speed data CarTrack returns. |
| **Ignition** and **Idling** | Binary sensors for the corresponding vehicle states. |
| **Speed** | Vehicle speed in km/h. |
| **Odometer** | Odometer reading in km. |
| **Battery voltage** | External vehicle battery voltage in volts, when reported by CarTrack. |
| **TCU battery level** | Telematics unit battery level as a percentage. |
| **Engine RPM** | Engine revolutions per minute. |
| **Engine runtime** | Accumulated engine-on time in minutes. |
| **Location** | Device tracker using the vehicle coordinates returned by CarTrack; includes an `altitude` attribute in meters when available. |
| **CarWatch** | Switch to activate or deactivate CarWatch for the vehicle. |

The **Status** sensor also exposes other available vehicle data as attributes, such as registration, event time, bearing, fuel, electric-vehicle details, and driver name. These fields depend on what CarTrack reports for the vehicle; missing data is not fabricated. CarWatch state is also included as a status attribute when available.

The CarWatch switch is created for each vehicle, but CarTrack must report its current state for the switch to show on or off. Changing the switch requires API credentials with permission to manage CarWatch. The API key is used as the password for HTTP Basic Authentication.

An account-level **API requests** sensor reports requests made by this integration during the trailing minute. Its attributes show per-endpoint counts and the documented per-minute limits, including the 60-request limit for `GET /vehicles/status`. The API also applies a default limit of 1,000 requests per minute. Counts are local to this integration and do not include calls made by other applications using the account.

## Polling

The integration polls every 1.5 seconds to leave headroom below CarTrack's 60-requests-per-minute limit for `GET /vehicles/status`. The polling rate is fixed; there is no user-configurable rate. If CarTrack returns `429 Too Many Requests`, the integration observes its retry headers and backs off with jitter. Each update also requests CarWatch status, which is covered by CarTrack's default 1,000-requests-per-minute limit.

## Development

The following instructions are for developing this integration, not required for a HACS installation.

### Development Home Assistant

Install Docker Desktop, then start the development instance from the repository root:

```powershell
docker compose up -d
```

Open `http://localhost:8123` and complete the initial Home Assistant setup. The integration directory is bind-mounted from this repository, so source changes are picked up after reloading the integration or restarting the container. Stop the instance with `docker compose down`; its configuration is kept in `dev/config`.

### VS Code Dev Container

Install the VS Code **Dev Containers** extension, then run **Dev Containers: Reopen in Container**. The container installs Home Assistant, pytest, and Ruff; Home Assistant starts with the CarTrack integration mounted from the workspace. Open `http://localhost:8123` and complete setup. Use **Run and Debug → Attach to Home Assistant** to attach breakpoints to the integration. In the integrated terminal, run `python -m pytest` and `python -m ruff check custom_components tests`.

The devcontainer and the standalone Home Assistant service use the same port and configuration, so run one at a time. To use the standalone service instead, run `docker compose --profile standalone up -d homeassistant`.

### Tests

Use Python 3.12 or newer in a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements_test.txt
python -m pytest
python -m ruff check custom_components tests
```

Tests mock the CarTrack API and do not require account credentials or a live CarTrack service. Never commit API keys or a populated Home Assistant configuration.
