# Vault Maintenance

> Config variables used below (`$OBSIDIAN_VAULT`, `$OBSIDIAN_VAULT_NAME`, `$OBSIDIAN_ICLOUD`, `$CLI`) are defined in the obsidian skill's [SKILL.md](../SKILL.md#configuration).

Storage analysis and backups.

## Storage Analysis

```bash
# Total vault size
du -sh "$OBSIDIAN_ICLOUD"

# Size by folder
du -sh "$OBSIDIAN_ICLOUD"/* | sort -hr | head -20

# Largest files
find "$OBSIDIAN_ICLOUD" -type f -exec du -h {} + 2>/dev/null | sort -hr | head -20

# Clean Smart Connections cache (regenerates automatically)
rm -rf "$OBSIDIAN_ICLOUD/.smart-env"
```

---

## Backup

```bash
# Create timestamped backup
mkdir -p ~/Downloads/VaultBackup && \
cd "$(dirname "$OBSIDIAN_ICLOUD")" && \
zip -r ~/Downloads/VaultBackup/"${OBSIDIAN_VAULT_NAME}_$(date +%Y-%m-%d_%H-%M-%S).zip" "$(basename "$OBSIDIAN_ICLOUD")" \
  -x "*.DS_Store" -x "*/.obsidian/workspace*.json" -x "*/.smart-env/*"

# List backups
ls -lah ~/Downloads/VaultBackup/*.zip 2>/dev/null

# Delete old backups (keep last 5)
cd ~/Downloads/VaultBackup && ls -t *.zip 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null
```

---
