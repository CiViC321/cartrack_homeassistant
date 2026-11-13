# CarTrack for Home Assistant

This repository provides a Home Assistant custom integration for CarTrack Fleet API. Home Assistant integrations create entities; add-ons run separate services and cannot create entities on their own.

## Install

Copy `custom_components/cartrack` into the Home Assistant configuration directory under `custom_components/cartrack`, then restart Home Assistant. Alternatively, add this repository to HACS as a custom integration.

In Home Assistant, go to **Settings → Devices & services → Add integration → CarTrack**. Enter the account username and API key, then select the CarTrack region. The integration selects the corresponding Fleet API base URL from the [documented region list](https://developer.cartrack.com/docs/fleet-api-general/base-url). The API key is used as the HTTP Basic Auth password.

Add the integration again for each additional account. Each entry polls independently and creates a device for each vehicle, with ignition and idling binary sensors, speed and odometer sensors, a location tracker, a status sensor, and a CarWatch switch. The status sensor also includes fuel, driver, and electric vehicle details as available from CarTrack. CarWatch switches require the API key to have permission to change CarWatch settings.

Configure the non-parked polling interval in the integration options (2–60 seconds; default 5 seconds). When all vehicles report parked, the integration polls every 60 seconds.

## Development Home Assistant

Install Docker Desktop, then start the development instance from the repository root:

```powershell
docker compose up -d
```

Open `http://localhost:8123` and complete the initial Home Assistant setup. The integration directory is bind-mounted from this repository, so source changes are picked up after reloading the integration or restarting the container. Stop the instance with `docker compose down`; its configuration is kept in `dev/config`.

## VS Code Dev Container

Install the VS Code **Dev Containers** extension, then run **Dev Containers: Reopen in Container**. The container installs Home Assistant, pytest, and Ruff; Home Assistant starts with the CarTrack integration mounted from the workspace. Open `http://localhost:8123` and complete setup. Use **Run and Debug → Attach to Home Assistant** to attach breakpoints to the integration. In the integrated terminal, run `python -m pytest` and `python -m ruff check custom_components tests`.

The devcontainer and the standalone Home Assistant service use the same port and configuration, so run one at a time. To use the standalone service instead, run `docker compose --profile standalone up -d homeassistant`.

## Tests

Use Python 3.12 or newer in a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements_test.txt
python -m pytest
python -m ruff check custom_components tests
```

Tests mock the CarTrack API and do not require account credentials or a live CarTrack service. Never commit API keys or a populated Home Assistant configuration.
