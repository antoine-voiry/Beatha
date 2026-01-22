# Project Beatha - Claude Context

## Deployment & Setup

### Deployment from Mac to Pi
```bash
./scripts/push_to_pi.sh antoine@beatha.local
```

### Initial Setup on Pi
```bash
antoine@beatha:~/beatha-project $ sudo ./scripts/setup.sh
```

## Known Issues

### Issue #1: Backend Python doesn't get started by setup.sh
**Status**: Active
**Impact**: After running setup.sh, the backend service may not start properly
**Workaround**: Manually restart with `sudo systemctl restart beatha`
