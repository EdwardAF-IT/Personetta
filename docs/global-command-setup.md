# Making personetta Available Everywhere

**Goal:** Type `personetta` at any command prompt, from any directory, and have it just work.

---

## Quick Start

### Step 1: Run the Setup Script

**One command for everything - same experience for feed and local users:**

**From Azure Artifacts feed (after pip install):**
```powershell
personetta setup
```

**From local repository:**
```powershell
.\scripts\Setup-Personetta.ps1
```

Both approaches:
- ✓ Auto-detect feed vs local repository installation
- ✓ Install personetta correctly
- ✓ Ensure global command access
- ✓ Configure PowerShell profile
- ✓ Are idempotent (safe to run multiple times)

**Options:**

Feed users:
```powershell
# Extract setup script without running it
personetta setup --extract-only

# Run with options
personetta setup --from-feed --pat 'your-pat-here'
personetta setup --skip-profile
personetta setup --skip-path-check
```

Local repo users:
```powershell
# Force feed installation
.\scripts\Setup-Personetta.ps1 -FromFeed -Pat 'your-pat-here'

# Force local installation
.\scripts\Setup-Personetta.ps1 -FromLocal

# Build wheel and install from it (test distribution)
.\scripts\Setup-Personetta.ps1 -FromLocal -BuildWheel

# Skip profile modifications
.\scripts\Setup-Personetta.ps1 -SkipProfile

# Skip PATH check (NOT RECOMMENDED - shows multiple warnings!)
.\scripts\Setup-Personetta.ps1 -SkipPathCheck
```

Close and reopen your terminal/PowerShell window.

### Step 3: Test

```bash
cd ~
personetta --version

cd /tmp
personetta list
```

✅ **It works!** You can now use `personetta` from anywhere.

**Having issues?** Run diagnostics:
```powershell
.\tests\Test-SetupScript.ps1
```

This test suite provides:
- Detailed diagnostics for each step
- Exact fix commands for any issues
- Quick vs comprehensive testing modes

See [tests/setup-tests.md](../tests/setup-tests.md) for more information.

---

## Understanding How It Works

### What Happens During Installation?

When you install personetta with pip:

1. **Package files** are copied to Python's site-packages directory
2. **Entry point script** (`personetta.exe` on Windows) is created in Python's Scripts directory
3. **Your shell** needs that Scripts directory in its PATH to find the command

### The Entry Point

In `pyproject.toml`:
```toml
[project.scripts]
personetta = "generator.cli.main:main"
```

This tells Python to create an executable named `personetta` that calls the `main()` function from `generator.cli.main`.

### Typical Script Locations

**Windows:**
- System install: `C:\PythonXX\Scripts\personetta.exe`
- User install: `%APPDATA%\Python\PythonXX\Scripts\personetta.exe`
- Example: `C:\Users\YourName\AppData\Roaming\Python\Python311\Scripts\personetta.exe`

**Linux/Mac:**
- System install: `/usr/local/bin/personetta`
- User install: `~/.local/bin/personetta`

### Setup Scripts for Feed Users

Feed users get the same setup experience as local repository users!

When you install from the Azure Artifacts feed, the setup scripts are **packaged with the distribution**. They're available at:

**Windows:**
```
%APPDATA%\Python\PythonXX\site-packages\scripts\Setup-Personetta.ps1
```

**Access via CLI:**
```powershell
# Run setup directly
personetta setup

# Or extract the script first
personetta setup --extract-only
```

The `personetta setup` command:
- Locates the bundled Setup-Personetta.ps1 script
- Runs it with the same options as local repo users
- Provides identical setup experience regardless of installation source

---

## Three Ways to Run personetta

### 1. Direct Command (Requires PATH Setup)

```bash
personetta --version
personetta list
personetta install '*' --format cursor
```

**Pros:**
- Cleanest, simplest syntax
- Works from any directory
- Standard CLI experience

**Cons:**
- Requires Scripts folder in PATH
- Needs terminal restart after PATH changes

### 2. Python Module Form (Always Works)

```bash
python -m generator.cli.main --version
python -m generator.cli.main list
python -m generator.cli.main install '*' --format cursor
```

**Pros:**
- Works immediately after install
- No PATH configuration needed
- Works even in weird environments

**Cons:**
- More verbose
- Less convenient for frequent use

### 3. PowerShell Alias (Convenience)

Add to your PowerShell profile:
```powershell
function Invoke-Personetta { python -m generator.cli.main @args }
Set-Alias -Name pn -Value Invoke-Personetta
```

Then use:
```powershell
pn --version
pn list
pn install '*' --format cursor
```

**Pros:**
- Short and convenient
- No PATH needed
- Automatically available in all sessions

**Cons:**
- PowerShell-only
- Requires profile modification

See [`scripts/Profile-Helper.ps1`](../scripts/Profile-Helper.ps1) for a complete profile helper.

---

## Troubleshooting

### Command Not Found: personetta

#### Diagnostic Script (Recommended)

```powershell
.\scripts\Setup-Personetta.ps1
```

This is the main setup script. It's idempotent and will:
1. ✓ Check Python installation
2. ✓ Verify personetta package is installed (or install it)
3. ✓ Locate the executable (handles venv vs user vs system installs)
4. ✓ Check if Scripts folder is in PATH
5. ✓ Add to PATH if needed
6. ✓ Configure PowerShell profile
7. ✓ Test both module and command forms

**Options:**
- `-BuildWheel`: Build wheel and install from it (test distribution packaging)
- `-SkipProfile`: Don't modify PowerShell profile
- `-SkipPathCheck`: Skip PATH validation (NOT RECOMMENDED - see warning below)

**⚠️ Warning about -SkipPathCheck:**

If you use `-SkipPathCheck`, the setup script will show THREE warnings:

1. **Upfront confirmation prompt**: "PATH check will be skipped. The personetta command may not work. Continue?"
2. **Yellow warning during execution**: "⚠ Skipping PATH check as requested"
3. **Red warning box at the end** with four fix options:
   - Run setup again without -SkipPathCheck
   - Add Scripts directory to PATH manually
   - Use `python -m generator.cli.main` instead
   - Configure PowerShell profile with helper functions

These warnings exist because skipping PATH configuration means the `personetta` command won't work from any directory.

**For diagnostic only (no installation):**
```powershell
.\scripts\Ensure-GlobalCommand.ps1
```

This is a lighter script that only checks and fixes PATH, without installing or configuring profile.

**For comprehensive diagnostics:**
```powershell
.\tests\Test-SetupScript.ps1
```

Runs 28 tests covering environment validation, syntax, build, installation, and command availability. Provides detailed fix commands for any issues. See [tests/setup-tests.md](../tests/setup-tests.md) for details.

#### Manual Diagnosis

**Step 1: Is personetta installed?**
```bash
python -m pip show personetta
```

If not found:
```bash
pip install --user personetta
```

**Step 2: Where is the executable?**
```bash
python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
```

Check if `personetta.exe` (Windows) or `personetta` (Linux/Mac) exists in that directory.

**Step 3: Is Scripts in PATH?**

Windows PowerShell:
```powershell
$env:PATH -split ';' | Where-Object { $_ -like '*Python*Scripts*' }
```

Linux/Mac:
```bash
echo $PATH | tr ':' '\n' | grep -i 'python\|\.local/bin'
```

**Step 4: Add to PATH if missing**

Windows PowerShell (permanent):
```powershell
$scriptsPath = python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
$currentPath = [Environment]::GetEnvironmentVariable('PATH', 'User')
[Environment]::SetEnvironmentVariable('PATH', "$currentPath;$scriptsPath", 'User')
```

Linux/Mac (add to `~/.bashrc` or `~/.zshrc`):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

**Step 5: Restart terminal**

Close and reopen your terminal window.

### Works with python -m but not as direct command

This means:
- ✓ Package is installed correctly
- ✓ Python can find the module
- ✗ Scripts folder is not in PATH (or terminal not restarted)

**Solution:** Run the diagnostic script or manually add to PATH as shown above.

### Works in one terminal but not another

This usually means:
- PATH change was only applied to current session, not permanently
- Different terminal types (cmd vs PowerShell vs bash) have different PATHs

**Solution:** 
1. Apply PATH change at the User or System level (not session)
2. Restart ALL terminals after PATH change

### Works as admin but not as regular user

This means:
- Package was installed with `pip install` (system-wide, requires admin)
- Scripts folder is in system PATH but not user PATH

**Solution:**
```bash
pip install --user personetta  # Reinstall as user
```

### Multiple Python versions

If you have Python 3.10, 3.11, 3.12, etc., each has its own Scripts folder.

**Check which Python runs personetta:**
```bash
python --version            # Check default Python
personetta --version        # Check if it works
python -m generator.cli.main --version  # Always works with default Python
```

**To use specific Python version:**
```bash
python3.11 -m pip install --user personetta
python3.11 -m generator.cli.main --version
```

Then add that specific Scripts folder to PATH.

---

## Best Practices

### For End Users (Feed Installation)

1. **Use the automated setup:**
   ```powershell
   .\scripts\Setup-Personetta.ps1 -FromFeed -Pat 'your-pat-here'
   ```

2. **Restart terminal after first install**

3. **Use direct command form:**
   ```bash
   personetta install '*' --format cursor
   ```

### For Developers (Local Repository)

1. **Use the automated setup:**
   ```powershell
   .\scripts\Setup-Personetta.ps1 -FromLocal
   ```

2. **Or manual install with auto-fix:**
   ```bash
   pip install --user -e ".[dev]"
   .\scripts\Setup-Personetta.ps1  # Fixes PATH and profile
   ```

3. **Use either form:**
   ```bash
   personetta list                          # Direct command
   python -m generator.cli.main list       # Module form
   pn list                                  # Alias (if profile configured)
   ```

### For CI/CD and Scripts

**Always use the module form:**
```bash
python -m generator.cli.main --version
python -m generator.cli.main validate
python -m generator.cli.main install '*' --format cursor --target global
```

This ensures:
- Works regardless of PATH configuration
- Works in containers and restricted environments
- Consistent across all platforms

---

## Platform-Specific Notes

### Windows

- **Default user Scripts location:** `%APPDATA%\Python\Python311\Scripts`
- **System Scripts location:** `C:\Python311\Scripts`
- **PATH separator:** `;` (semicolon)
- **Executable name:** `personetta.exe`

**Check PATH:**
```powershell
$env:PATH -split ';'
```

**Add to PATH (User level):**
```powershell
[Environment]::SetEnvironmentVariable('PATH', "$env:PATH;$scriptsPath", 'User')
```

### Linux

- **User Scripts location:** `~/.local/bin`
- **System Scripts location:** `/usr/local/bin`
- **PATH separator:** `:` (colon)
- **Executable name:** `personetta`

**Check PATH:**
```bash
echo $PATH | tr ':' '\n'
```

**Add to PATH (bash):**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### macOS

- **User Scripts location:** `~/Library/Python/3.11/bin` or `~/.local/bin`
- **System Scripts location:** `/usr/local/bin`
- **PATH separator:** `:` (colon)
- **Executable name:** `personetta`

**Check PATH:**
```bash
echo $PATH | tr ':' '\n'
```

**Add to PATH (zsh - default on macOS):**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

## Verification Checklist

After setup, verify everything works:

- [ ] `python --version` shows 3.11 or higher
- [ ] `python -m pip show personetta` shows package info
- [ ] `python -m generator.cli.main --version` displays version
- [ ] `personetta --version` displays version (after terminal restart)
- [ ] Command works from home directory: `cd ~ && personetta list`
- [ ] Command works from temp directory: `cd /tmp && personetta list`
- [ ] Command works from any arbitrary directory

✅ **All checks pass?** You're ready to use personetta everywhere!

---

## Quick Reference

| Scenario | Command | Notes |
|----------|---------|-------|
| First-time setup (any) | `.\scripts\Setup-Personetta.ps1` | Handles everything automatically |
| Force feed install | `.\scripts\Setup-Personetta.ps1 -FromFeed -Pat 'xxx'` | With PAT |
| Force local install | `.\scripts\Setup-Personetta.ps1 -FromLocal` | From repository |
| Diagnostic only | `.\scripts\Ensure-GlobalCommand.ps1` | Check/fix PATH without install |
| Test installation | `personetta --version` | Should work from any directory |
| Fallback (always works) | `python -m generator.cli.main <cmd>` | No PATH needed |
| Profile alias | `pn <cmd>` | If profile configured by Setup-Personetta |
| Check installation | `python -m pip show personetta` | Shows version and location |
| Find Scripts folder | `python -c "import sysconfig; print(sysconfig.get_path('scripts'))"` | Where executable lives |
| Check PATH | `$env:PATH -split ';'` (Win) or `echo $PATH` (Linux/Mac) | Should include Scripts folder |
| Upgrade | `.\scripts\Setup-Personetta.ps1 -FromFeed` (feed) or `pip install --user --upgrade personetta` | Get latest version |

---

## Summary

**The goal is simple:** `personetta` should work from any directory, whether installed from feed or local repo.

**One-step process:**
1. **Run** `.\scripts\Setup-Personetta.ps1` - handles everything
2. **Restart** terminal for PATH changes to take effect
3. **Test** with `personetta --version`

**Three ways to run:**
1. **`personetta`** - Direct command (cleanest, requires PATH)
2. **`python -m generator.cli.main`** - Module form (always works)
3. **`pn`** - Alias (convenient, requires profile setup)

**When in doubt:**
- Run `.\scripts\Setup-Personetta.ps1` for automatic setup
- Use `python -m generator.cli.main` form as immediate fallback
- See [troubleshooting.md](troubleshooting.md) for detailed debugging

**It should "just work"** after proper setup, regardless of installation method or current directory. 🎯
