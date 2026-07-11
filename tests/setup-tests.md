# Setup Script Tests

Comprehensive test suite for `scripts/Setup-Personetta.ps1`.

## Running Tests

```powershell
# Run all tests
.\tests\Test-SetupScript.ps1

# Run quick smoke tests only
.\tests\Test-SetupScript.ps1 -Quick
```

## Test Categories

### 1. Environment Validation
- ✅ Setup script exists
- ✅ pyproject.toml exists
- ✅ Python 3.11+ is available

### 2. Script Syntax and Parameters
- ✅ PowerShell syntax is valid
- ✅ Help documentation exists
- ✅ All parameters are defined

### 3. Virtual Environment Detection
- ✅ Detects current environment (venv vs global)
- ✅ Shows Python paths for debugging

### 4. Build Functionality
- ✅ Can build wheel package
- ✅ Wheel contains scripts directory
- ✅ Setup-Personetta.ps1 included in wheel

### 5. Command Availability
- ✅ personetta command or module is available
- ✅ Diagnoses PATH issues with fix commands
- ✅ Shows executable location

### 6. Setup Command
- ✅ `personetta setup` command exists
- ✅ Has --extract-only option
- ✅ Has --from-feed option

## Common Issues and Fixes

### Issue: "personetta: The term 'personetta' is not recognized"

**Diagnosis:**
Run the test script - it will show exactly what's wrong:
```powershell
.\tests\Test-SetupScript.ps1
```

**Common causes:**
1. **Scripts directory not in PATH** (most common)
   - Executable exists at: `C:\Users\<you>\AppData\Roaming\Python\Python313\Scripts\personetta.exe`
   - But that directory is not in your PATH
   
   **Fix:**
   ```powershell
   # Permanent fix
   .\scripts\Setup-Personetta.ps1 -FromLocal
   
   # Or temporary (current session only)
   $env:PATH = "$env:APPDATA\Python\Python313\Scripts;" + $env:PATH
   ```

2. **Installed in venv but venv not activated**
   - Executable at: `.venv\Scripts\personetta.exe`
   - But venv is not active
   
   **Fix:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   personetta --version
   ```

3. **Not installed at all**
   
   **Fix:**
   ```powershell
   .\scripts\Setup-Personetta.ps1 -FromLocal
   ```

### Issue: Tests fail with "BuildWheel parameter not found"

**Cause:** Running an old version of Setup-Personetta.ps1

**Fix:**
```powershell
# Update to latest
git pull
.\tests\Test-SetupScript.ps1
```

## Integration Testing

The test script includes **non-destructive** tests that don't modify your system. For full integration testing in clean environments:

### Test Local Editable Install
```powershell
# In repo directory
.\scripts\Setup-Personetta.ps1 -FromLocal
personetta --version
personetta list
```

### Test Local Wheel Install
```powershell
# Build and install from wheel
.\scripts\Setup-Personetta.ps1 -FromLocal -BuildWheel
personetta --version
```

### Test Feed Install (requires PAT)
```powershell
# From feed
.\scripts\Setup-Personetta.ps1 -FromFeed -Pat '<your-pat>'
personetta --version
```

### Test Venv Install
```powershell
# Create fresh venv
python -m venv test-venv
.\test-venv\Scripts\Activate.ps1

# Install in venv
.\scripts\Setup-Personetta.ps1 -FromLocal
personetta --version

# Cleanup
deactivate
Remove-Item test-venv -Recurse -Force
```

## Test Development

### Adding New Tests

1. Add test function following the pattern:
```powershell
Write-TestCase "Your test description"
Assert-True -Condition $someCheck -Message "What you're testing"
```

2. Use assertions:
- `Assert-True` - Boolean check
- `Assert-Equal` - Value comparison
- `Assert-FileExists` - File existence
- `Skip-Test` - Skip with reason

### Test Output

- ✓ PASS: Green - test passed
- ✗ FAIL: Red - test failed
- ⊘ SKIP: Gray - test skipped
- ℹ Info: Cyan - diagnostic information
- ⚠ Warning: Yellow - non-fatal issue

## CI/CD Integration

Add to your CI pipeline:

```yaml
# Azure Pipelines example
- task: PowerShell@2
  displayName: 'Run Setup Script Tests'
  inputs:
    targetType: 'filePath'
    filePath: 'tests/Test-SetupScript.ps1'
    failOnStderr: false
```

## Future Enhancements

- [ ] Add --WhatIf dry-run mode to setup script
- [ ] Docker-based isolated integration tests
- [ ] Automated cross-platform testing (Linux, macOS)
- [ ] Performance benchmarks for build/install
- [ ] Test profile modification idempotency
- [ ] Test PATH modification scenarios
