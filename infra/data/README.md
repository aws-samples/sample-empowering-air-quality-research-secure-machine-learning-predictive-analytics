# Air Quality Data Setup Guide

## Overview

This directory is where you manage your air quality dataset for the ML system. The system provides two flexible approaches for handling your data file, allowing you to choose the method that best fits your file size and deployment preferences.

## Data File Setup Options

### Option 1: Local File Approach

**Best for**: Smaller files (<100MB), simple setup

#### Steps:
1. Place your CSV file at `infra/data/init_data.csv` (or your configured filename)
2. Verify CSV format matches required schema (see format details below)
3. Deploy: `./bin/setup.sh --use-defaults --deploy`
4. Run database initialization Lambda function in AWS Console

#### Benefits:
- Simple one-step deployment
- File is included in the deployment package
- Good for smaller datasets
- Immediate deployment readiness

### Option 2: S3 Upload Approach

**Best for**: Large files (>100MB), production deployments

#### Steps:
1. Deploy infrastructure first: `./bin/setup.sh --use-defaults --deploy`
2. Upload your CSV file to S3 bucket location: `initial_dataset/`
3. Run database initialization Lambda function in AWS Console
4. Lambda processes file from S3 and populates database

#### Benefits:
- Handles large files efficiently
- Separates infrastructure deployment from data loading
- More scalable approach
- Better for production environments
- No file size limitations

### S3 Upload Details

#### Bucket Location:
- **Path**: `initial_dataset/`
- **Filename**: Use your configured filename (default: `init_data.csv`)

#### After Upload:
1. Go to AWS Console → Lambda
2. Find the database initialization function
3. Execute the function
4. It will automatically:
   - Detect the file in S3
   - Process the CSV data
   - Populate the RDS database
   - Prepare the system for predictions

### Choosing the Right Approach

| Factor | Local File | S3 Upload |
|--------|------------|-----------|
| File Size | < 100MB | Any size |
| Setup Complexity | Simple | Moderate |
| Deployment Speed | Fast | Moderate |
| Scalability | Limited | High |
| Production Ready | Basic | Yes |
| File Management | Local | Cloud-based |

## CSV Format Requirements

Both approaches require the same CSV format with all required columns present.

### Required CSV Fields

Your CSV file must contain the following columns (order is flexible):

```csv
timestamp,value,parameter,device_id,chip_id,sensor_type,sensor_id,location_id,location,street_name,city,country,latitude,longitude,deployment_date
```

**Important**: The system uses column headers to identify fields, so column order doesn't matter as long as all required headers are present.

### Example Data Row

```csv
2023-07-15 09:22:31.456 +0200,25.4,PM 2.5,24,esp8266-87654322,2,38,43,City Center,Oak Avenue,Springfield,United States,38.7823456,-92.1245678,2022-05-12 08:45:22.310 +0200
```

### Column Descriptions

| Column | Description | Data Type | Example |
|--------|-------------|-----------|---------|
| `timestamp` | Date and time with timezone | DateTime with TZ | `2023-07-15 09:22:31.456 +0200` |
| `value` | Sensor reading value | Numeric | `25.4` |
| `parameter` | Type of measurement | String | `PM 2.5`, `Temperature`, `Humidity`, `CO2`, etc. |
| `device_id` | Unique device identifier | Integer | `23` |
| `chip_id` | Chip identifier | String | `esp8266-87654321` |
| `sensor_type` | Type of sensor | Integer | `1`, `2`, `3`, `4` |
| `sensor_id` | Unique sensor identifier | Integer | `37` |
| `location_id` | Location identifier | Integer | `42` |
| `location` | Location name | String | `ABC University` |
| `street_name` | Street address | String | `Main Street` |
| `city` | City name | String | `Springfield` |
| `country` | Country name | String | `United States` |
| `latitude` | GPS latitude coordinate | Decimal | `38.7812345` |
| `longitude` | GPS longitude coordinate | Decimal | `-92.1234567` |
| `deployment_date` | When sensor was deployed | DateTime with TZ | `2022-05-12 08:45:22.310 +0200` |

### Field Requirements

#### Timestamp Fields
- **Format**: Include timezone information (e.g., `+0200`, `-0500`)
- **Precision**: Milliseconds are supported but optional
- **Example**: `2023-07-15 09:22:31.456 +0200`

#### Parameter Field
- **Flexible Values**: Can contain any measurement type (PM 2.5, Temperature, Humidity, CO2, etc.)
- **No Restrictions**: Not limited to air quality parameters
- **Prediction Target**: The system will use your configured parameter for ML predictions
- **Case Sensitive**: Ensure consistent naming throughout your dataset

#### Location Fields
- **GPS Coordinates**: Use decimal degrees format
- **Addresses**: Provide complete address information
- **Location Names**: Descriptive names for sensor locations

### CSV Format Flexibility

#### Column Order
- ✅ **Flexible**: Columns can be in any order
- ✅ **Header-Based**: System identifies fields by column names
- ✅ **Example**: `value,timestamp,parameter,...` is perfectly valid

#### Parameter Values
- ✅ **Any Measurement**: Temperature, Humidity, CO2, PM 2.5, PM 10, etc.
- ✅ **Custom Parameters**: Use your own measurement names
- ✅ **Multiple Types**: Your dataset can contain various parameter types
- ✅ **Prediction Focus**: ML model will focus on your configured parameter

#### Example Valid CSV Structures
```csv
# Option 1: Standard order
timestamp,value,parameter,device_id,...

# Option 2: Different order
parameter,value,timestamp,location,...

# Option 3: Any order you prefer
device_id,parameter,timestamp,value,...
```
## File Preparation Guidelines

### Before Deployment
- ✅ **Required**: Ensure all required column headers are present
- ✅ **Headers**: Column names must match exactly (case sensitive)
- ✅ **Encoding**: Use UTF-8 encoding for your CSV file
- ✅ **Header Row**: Include the header row as the first line
- ✅ **Timezone**: All timestamps must include timezone information

### Data Quality Tips
- **Consistent Timestamps**: Ensure all timestamps use the same timezone
- **Valid GPS Coordinates**: Latitude should be between -90 and 90, longitude between -180 and 180
- **Consistent Parameters**: Use consistent naming for parameter values
- **Complete Addresses**: Provide full location information for better analysis
- **Multiple Parameters**: Your dataset can contain various measurement types

### File Size Considerations
- **Local Approach**: Best for files under 100MB
- **S3 Approach**: Handles any file size efficiently
- **Processing Time**: Large files may take longer to process
- **Lambda Timeout**: Database initialization has a 15-minute timeout limit

## Troubleshooting

### Local File Issues
- **File Location**: Ensure file exists at exact path: `infra/data/init_data.csv`
- **File Permissions**: Check file permissions are readable
- **CSV Format**: Verify CSV format and encoding
- **File Size**: Consider S3 approach for files >100MB

### S3 Upload Issues
- **Upload Location**: Confirm file uploaded to correct S3 location (`initial_dataset/`)
- **Permissions**: Check Lambda function has S3 read permissions
- **Logs**: Verify database initialization Lambda execution logs in CloudWatch
- **Database Access**: Ensure RDS database is accessible from Lambda
- **File Name**: Use the same filename as configured in your setup

### Common Format Issues
1. **Missing Headers**: Ensure all required column names are present
2. **Header Spelling**: Column names must match exactly (case sensitive)
3. **Encoding Issues**: Save CSV as UTF-8
4. **Date Format**: Include timezone in timestamp fields
5. **Missing Values**: Ensure no empty cells in required columns
6. **GPS Format**: Use decimal degrees, not degrees/minutes/seconds

### Validation Checklist

Before deployment, verify:
- [ ] CSV file is in correct location with proper filename
- [ ] All required headers are present (order doesn't matter)
- [ ] Header names match exactly (case sensitive)
- [ ] All timestamp fields include timezone information
- [ ] Parameter field contains your measurement types
- [ ] GPS coordinates are in decimal degrees format
- [ ] No empty cells in required columns
- [ ] File is saved as UTF-8 encoding
- [ ] File size is appropriate for chosen approach

## Data Processing

### Automatic Processing
- The database initialization Lambda function will automatically process your CSV file
- Data will be imported into the PostgreSQL database
- The system will use your configured parameter for machine learning predictions
- Other parameters in your dataset will be stored but not used for ML training

### Processing Steps
1. **File Detection**: Lambda detects CSV file (local or S3)
2. **Format Validation**: Verifies required headers and data types
3. **Data Import**: Imports data into PostgreSQL database
4. **Indexing**: Creates database indexes for efficient querying
5. **Validation**: Confirms successful import and data integrity

## Next Steps

### After Data Setup (Either Approach)
1. **Database Initialization**: Run the Lambda function to process your data
2. **Verify Import**: Check CloudWatch logs for successful processing
3. **Canvas Model**: Create your SageMaker Canvas model (follow blog post instructions)
4. **Update Configuration**: Edit `infra/scripts/post-deployment-config.ini` with Canvas model ID
5. **Re-deploy**: Run `cd infra && cdk deploy` to activate predictions
6. **System Ready**: Your air quality prediction system is ready to use!

### Monitoring and Maintenance
- **CloudWatch Logs**: Monitor Lambda execution logs for any issues
- **Database Health**: Check RDS database performance and storage
- **Data Quality**: Regularly validate incoming sensor data
- **Model Performance**: Monitor prediction accuracy and retrain as needed

## Support

If you encounter issues with data formatting or processing:
1. Verify your CSV contains all required headers (order doesn't matter)
2. Check that parameter values are consistent in naming
3. Review CloudWatch logs for the database initialization Lambda
4. Ensure timestamps include proper timezone information
5. Confirm your configured parameter exists in your dataset
6. For S3 approach, verify file upload location and permissions
7. Check file encoding is UTF-8
8. Validate GPS coordinates are in decimal degrees format
