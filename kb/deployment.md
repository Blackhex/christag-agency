# Deployment

## Running Directly

```bash
pip install -e .
agency
# or: agency --port 8500 --host 0.0.0.0
```

Agency serves on `http://localhost:8500` by default.

## Running as a systemd User Service

A service template is provided at `agency.service.example`. Copy and customize it:

```bash
cp agency.service.example ~/.config/systemd/user/agency.service
# Edit the file to set your paths

systemctl --user daemon-reload
systemctl --user enable --now agency.service
```

### Service Management

```bash
systemctl --user status agency.service       # Check status
systemctl --user restart agency.service      # Restart after code changes
journalctl --user -u agency.service -f       # Stream logs
```

## Notes

- Agency assumes local/trusted access. There is no authentication.
- Use a **user-level** systemd service, not system-level. System services cannot access user home directories on immutable OSes like Fedora Kinoite.
- The Python venv should be at `.venv/` in the project directory. The service file should reference `.venv/bin/agency` or `.venv/bin/python`.
