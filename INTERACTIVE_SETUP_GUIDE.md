# Interactive Setup Guide

## Quick Start Options

### Option 1: Non-Interactive (Recommended for Quick Setup)
```bash
# Uses all default values automatically (setup only)
./bin/setup.sh --use-defaults

# OR setup and deploy in one command
./bin/setup.sh --use-defaults --deploy
```

### Option 2: Interactive (Recommended for Custom Configuration)
```bash
# Prompts for each configuration option (setup only)
./bin/setup.sh

# OR interactive setup with automatic deployment
./bin/setup.sh --deploy
```

## Interactive Mode Instructions

When you run the interactive setup, you'll see prompts like this:

### Step 1: Basic Configuration
```
📋 Step 1: Basic Configuration
Let's configure your air quality ML system with some basic settings.
💡 Tip: You can press Enter to use default values, or use --use-defaults flag for non-interactive setup

Enter project prefix (used for resource naming):
Default value: demoapp
Instructions: Type your value and press Enter, or just press Enter to use the default
> 
```

**What to do:**
- **Press Enter** to use the default value (`demoapp`)
- **Type a custom value** (like `myproject`) and press Enter to use your custom value

### Step 2: Data File Configuration
```
Enter your initial data filename:
Default value: init_data.csv
Instructions: Type your value and press Enter, or just press Enter to use the default
> 
```

**What to do:**
- **Press Enter** to use `init_data.csv`
- **Type your filename** (like `my_air_quality_data.csv`) and press Enter

### Step 3: Parameter Selection
```
Available air quality parameters (common examples):
  • PM 10   - Particulate matter 10 micrometers
  • PM 1    - Particulate matter 1 micrometer
  • PM 2.5  - Particulate matter 2.5 micrometers
  • Temperature, Humidity, CO2, etc. - Any measurement type

Enter the parameter for ML prediction (can be any measurement type):
Default value: PM 2.5
Instructions: Type your value and press Enter, or just press Enter to use the default
> 
```

**What to do:**
- **Press Enter** to use `PM 2.5`
- **Type your parameter** (like `Temperature` or `PM 10`) and press Enter

### Step 4: Canvas Model Discovery
```
📋 Step 2: Canvas Model Discovery
Now let's find your SageMaker Canvas model and endpoint.

🔍 Discovering your Canvas models...
✅ Found Canvas model: canvas-model-2025-02-18-23-55-02-559819

Enter your Canvas Model ID:
Default value: canvas-model-2025-02-18-23-55-02-559819
Instructions: Type your value and press Enter, or just press Enter to use the default
> 
```

**What to do:**
- **Press Enter** to use the discovered model
- **Type your model ID** if you want to use a different one

### Step 5: Configuration Confirmation
```
📋 Step 3: Configuration Summary
==============================================
Project Prefix:     demoapp
Data File:          init_data.csv
AQ Parameter:       PM 2.5
Canvas Model ID:    canvas-model-2025-02-18-23-55-02-559819
Canvas Endpoint:    canvas-AQDeployment

Continue with this configuration? (y/N): 
```

**What to do:**
- **Type `y`** and press Enter to continue
- **Type `n`** or just press Enter to cancel

## Troubleshooting

### Script Gets Stuck at Prompt
If you see:
```
📋 Step 1: Basic Configuration
Let's configure your air quality ML system with some basic settings.

> 
```

**Solutions:**
1. **Press Enter** - The script is waiting for your input
2. **Use non-interactive mode**: `./bin/setup.sh --use-defaults`
3. **Check your terminal** - Make sure you can type in the terminal

### Default Values
The script uses these default values:
- **Project Prefix**: `demoapp`
- **Data File**: `init_data.csv`
- **AQ Parameter**: `PM 2.5`
- **Canvas Endpoint**: `canvas-AQDeployment`

### Getting Help
```bash
# Show help and default values
./bin/setup.sh --help
```

## Complete Example Session

Here's what a complete interactive session looks like:

```
🚀 Air Quality ML System - Simple Setup
==============================================

📝 Running in interactive mode
💡 For non-interactive setup, use: ./bin/setup.sh --use-defaults

📋 Step 1: Basic Configuration
Let's configure your air quality ML system with some basic settings.
💡 Tip: You can press Enter to use default values, or use --use-defaults flag for non-interactive setup

Enter project prefix (used for resource naming):
Default value: demoapp
Instructions: Type your value and press Enter, or just press Enter to use the default
> [PRESS ENTER]
Using default: demoapp

Enter your initial data filename:
Default value: init_data.csv
Instructions: Type your value and press Enter, or just press Enter to use the default
> [PRESS ENTER]
Using default: init_data.csv

Available air quality parameters (common examples):
  • PM 10   - Particulate matter 10 micrometers
  • PM 1    - Particulate matter 1 micrometer
  • PM 2.5  - Particulate matter 2.5 micrometers
  • Temperature, Humidity, CO2, etc. - Any measurement type

Enter the parameter for ML prediction (can be any measurement type):
Default value: PM 2.5
Instructions: Type your value and press Enter, or just press Enter to use the default
> [PRESS ENTER]
Using default: PM 2.5

📋 Step 2: Canvas Model Discovery
Now let's find your SageMaker Canvas model and endpoint.

🔍 Discovering your Canvas models...
✅ Found Canvas model: canvas-model-2025-02-18-23-55-02-559819

Enter your Canvas Model ID:
Default value: canvas-model-2025-02-18-23-55-02-559819
Instructions: Type your value and press Enter, or just press Enter to use the default
> [PRESS ENTER]
Using default: canvas-model-2025-02-18-23-55-02-559819

Enter your Canvas Endpoint Name:
Default value: canvas-AQDeployment
Instructions: Type your value and press Enter, or just press Enter to use the default
> [PRESS ENTER]
Using default: canvas-AQDeployment

📋 Step 3: Configuration Summary
==============================================
Project Prefix:     demoapp
Data File:          init_data.csv
AQ Parameter:       PM 2.5
Canvas Model ID:    canvas-model-2025-02-18-23-55-02-559819
Canvas Endpoint:    canvas-AQDeployment

Continue with this configuration? (y/N): y

🔧 Step 4: Environment Setup
Setting up Python environment and dependencies...
[Setup continues...]
```

## Key Points

1. **Just Press Enter** - For most users, pressing Enter to use defaults is the easiest option
2. **Use Non-Interactive** - If you want to skip all prompts: `--use-defaults`
3. **Clear Instructions** - Each prompt shows exactly what to do
4. **Safe Defaults** - All default values are sensible and will work for most users
5. **Help Available** - Use `--help` to see all options and default values
