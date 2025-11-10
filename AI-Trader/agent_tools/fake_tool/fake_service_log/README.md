# Fake Service Logs

This directory contains log files for all fake MCP services.

## Log Files

When services are running, you'll find the following log files here:

### Real Services
- `math.log` - Math service logs (port 8000)
- `trade.log` - Trade service logs (port 8002)

### Fake Services
- `fake_search.log` - Fake search service logs (port 8001)
- `fake_price.log` - Fake price service logs (port 8003)
- `fake_x.log` - Fake X service logs (port 8004)
- `fake_reddit.log` - Fake Reddit service logs (port 8005)

## Viewing Logs

### View all fake service logs
```bash
tail -f fake_service_log/fake_*.log
```

### View specific service log
```bash
# Price service
tail -f fake_service_log/fake_price.log

# Search service
tail -f fake_service_log/fake_search.log

# X service
tail -f fake_service_log/fake_x.log

# Reddit service
tail -f fake_service_log/fake_reddit.log
```

### View real-time updates from all services
```bash
tail -f fake_service_log/*.log
```

### Search for specific events
```bash
# Find all hijack events
grep "HIJACK" fake_service_log/*.log

# Find errors
grep "ERROR\|❌" fake_service_log/*.log

# Find specific date queries
grep "2025-10-22" fake_service_log/fake_price.log
```

## Log Rotation

Logs are recreated each time services start. Old logs are overwritten.

If you want to preserve logs, copy them before restarting:

```bash
# Backup logs with timestamp
cp -r fake_service_log fake_service_log_backup_$(date +%Y%m%d_%H%M%S)

# Or archive them
tar -czf logs_$(date +%Y%m%d_%H%M%S).tar.gz fake_service_log/
```

## Troubleshooting

### No log files appearing?

1. Check if services are running:
   ```bash
   python start_fake_mcp_services.py status
   ```

2. Check directory permissions:
   ```bash
   ls -la fake_service_log/
   ```

3. Start services with verbose output:
   ```bash
   python start_fake_mcp_services.py
   # Watch for "Log files location: ..." message
   ```

### Log files too large?

Clean up old logs:
```bash
# Remove all log files
rm fake_service_log/*.log

# Or truncate them
truncate -s 0 fake_service_log/*.log
```

## Log Format

Each log file contains:
- Service startup information
- Request/response details
- Hijack notifications (fake services only)
- Error messages
- Service shutdown information

Example log entry:
```
🎯 HIJACK: Returning fake price for NVDA on 2025-10-22
   → Date: 2025-10-22
   → Fake open: $50.00
   → Scenario: Day 1
```

---

**Note**: These logs are for debugging and verification purposes. They help confirm that fake services are properly intercepting and manipulating data.


