# Air Quality Monitoring System - Architecture Diagram

## System Architecture Overview

```mermaid
graph TB
    %% External Data Sources
    subgraph "Data Sources"
        CSV[Air Quality CSV Data<br/>PM 2.5, PM 10, PM 1]
    end

    %% EventBridge Scheduler
    subgraph "Scheduling"
        EBS[EventBridge Scheduler<br/>24-hour intervals]
    end

    %% S3 Storage
    subgraph "Amazon S3 Storage"
        S3_INIT[Initial Dataset<br/>initial_dataset/]
        S3_RETRIEVED[Retrieved Data<br/>retrieved_from_db/]
        S3_BATCH_IN[Batch Input<br/>input_batch/]
        S3_BATCH_OUT[Batch Output<br/>output_batch/]
        S3_PREDICTED[Predicted Results<br/>predicted_values_output/]
        S3_METADATA[Job Metadata<br/>batch_job_metadata/]
    end

    %% VPC Container
    subgraph "Amazon VPC"
        %% Public Subnets
        subgraph "Public Subnets"
            NAT[NAT Gateway]
        end

        %% Private Subnets
        subgraph "Private Subnets"
            %% Lambda Functions
            subgraph "AWS Lambda Functions"
                L_INIT[DB Initialization<br/>Lambda]
                L_QUERY[Get Records<br/>Lambda]
                L_BATCH_INIT[Initiate Batch<br/>Transform Lambda]
                L_BATCH_CB[Batch Transform<br/>Callback Lambda]
                L_WRITE[Write Results<br/>Lambda]
            end

            %% Database
            subgraph "Amazon RDS"
                RDS[(Aurora PostgreSQL<br/>Cluster)]
                RDS_SECRET[AWS Secrets Manager<br/>DB Credentials]
            end

            %% SageMaker
            subgraph "Amazon SageMaker"
                SM_ENDPOINT[Canvas Model<br/>Endpoint]
                SM_BATCH[Batch Transform<br/>Jobs]
            end
        end
    end

    %% EventBridge for SageMaker Events
    subgraph "Amazon EventBridge"
        EB_RULE[SageMaker Transform<br/>Job State Change Rule]
    end

    %% Step Functions
    subgraph "AWS Step Functions"
        SF_START([Start])
        SF_QUERY[Query Database<br/>for New Records]
        SF_CHECK{Records<br/>Found?}
        SF_BATCH[Initiate Batch<br/>Transform]
        SF_WAIT[Wait for Task Token<br/>Callback]
        SF_WRITE[Write Results<br/>to Database]
        SF_END([End])
    end

    %% Parameter Store
    subgraph "AWS Systems Manager"
        SSM[Parameter Store<br/>Job Metadata]
    end

    %% IAM Roles
    subgraph "AWS IAM"
        IAM_INIT[DB Init Role]
        IAM_READER[DB Reader Role]
        IAM_WRITER[DB Writer Role]
        IAM_BATCH_INIT[Batch Initiate Role]
        IAM_BATCH_CB[Batch Callback Role]
        IAM_SF[Step Functions Role]
        IAM_SCHEDULER[Scheduler Role]
    end

    %% Data Flow Connections
    CSV --> S3_INIT
    EBS --> SF_START
    
    %% Step Functions Flow
    SF_START --> SF_QUERY
    SF_QUERY --> SF_CHECK
    SF_CHECK -->|Yes| SF_BATCH
    SF_CHECK -->|No| SF_END
    SF_BATCH --> SF_WAIT
    SF_WAIT --> SF_WRITE
    SF_WRITE --> SF_END

    %% Lambda to S3 connections
    L_INIT --> S3_INIT
    L_QUERY --> S3_RETRIEVED
    L_BATCH_INIT --> S3_BATCH_IN
    L_BATCH_INIT --> S3_BATCH_OUT
    L_BATCH_CB --> S3_BATCH_OUT
    L_WRITE --> S3_PREDICTED

    %% Lambda to Database connections
    L_INIT --> RDS
    L_QUERY --> RDS
    L_WRITE --> RDS
    L_INIT --> RDS_SECRET

    %% SageMaker connections
    L_BATCH_INIT --> SM_BATCH
    SM_BATCH --> SM_ENDPOINT
    SM_BATCH --> S3_BATCH_IN
    SM_BATCH --> S3_BATCH_OUT

    %% EventBridge connections (SageMaker job completion triggers callback)
    SM_BATCH --> EB_RULE
    EB_RULE --> L_BATCH_CB

    %% Callback Lambda sends task token back to Step Functions
    L_BATCH_CB -.-> SF_WAIT

    %% Step Functions to Lambda connections
    SF_QUERY --> L_QUERY
    SF_BATCH --> L_BATCH_INIT
    SF_WRITE --> L_WRITE

    %% Parameter Store connections
    L_BATCH_INIT --> SSM
    L_BATCH_CB --> SSM

    %% IAM Role associations
    IAM_INIT -.-> L_INIT
    IAM_READER -.-> L_QUERY
    IAM_BATCH_INIT -.-> L_BATCH_INIT
    IAM_BATCH_CB -.-> L_BATCH_CB
    IAM_WRITER -.-> L_WRITE
    IAM_SF -.-> SF_START
    IAM_SCHEDULER -.-> EBS

    %% Network connections
    NAT -.-> L_QUERY
    NAT -.-> L_BATCH_INIT
    NAT -.-> L_BATCH_CB
    NAT -.-> L_WRITE

    %% Styling
    classDef storage fill:#e1f5fe
    classDef compute fill:#f3e5f5
    classDef database fill:#e8f5e8
    classDef ml fill:#fff3e0
    classDef orchestration fill:#fce4ec
    classDef security fill:#f1f8e9

    class S3_INIT,S3_RETRIEVED,S3_BATCH_IN,S3_BATCH_OUT,S3_PREDICTED,S3_METADATA storage
    class L_INIT,L_QUERY,L_BATCH_INIT,L_BATCH_CB,L_WRITE compute
    class RDS,RDS_SECRET database
    class SM_ENDPOINT,SM_BATCH ml
    class SF_START,SF_QUERY,SF_CHECK,SF_BATCH,SF_WAIT,SF_WRITE,SF_END,EBS,EB_RULE orchestration
    class IAM_INIT,IAM_READER,IAM_WRITER,IAM_BATCH_INIT,IAM_BATCH_CB,IAM_SF,IAM_SCHEDULER security
```

## Detailed Component Description

### 1. Data Ingestion Layer
- **CSV Data Sources**: Air quality sensor data containing PM 2.5, PM 10, and PM 1 measurements
- **S3 Initial Dataset**: Raw sensor data uploaded to `initial_dataset/` prefix
- **Configuration**: Users can select which parameter (PM 2.5, PM 10, or PM 1) to focus on for predictions

### 2. Scheduling & Orchestration
- **EventBridge Scheduler**: Triggers the workflow every 24 hours
- **EventBridge Rules**: Monitor SageMaker batch transform job state changes
- **Step Functions State Machine**: Orchestrates the entire data processing pipeline
  - Queries database for new records
  - Initiates batch transform jobs
  - Waits for task token callback (not direct completion)
  - Writes results back to database

### 3. Compute Layer (AWS Lambda)
- **DB Initialization Lambda**: Sets up database schema and loads initial data
- **Get Records Lambda**: Queries database for unprocessed records matching selected parameter
- **Initiate Batch Transform Lambda**: Creates SageMaker batch transform jobs and stores task tokens
- **Batch Transform Callback Lambda**: Triggered by EventBridge when jobs complete, sends task tokens back to Step Functions
- **Write Results Lambda**: Stores prediction results back to database

### 4. Machine Learning Layer
- **SageMaker Canvas Model Endpoint**: Pre-trained model for air quality predictions
- **Batch Transform Jobs**: Processes large datasets efficiently
- **Model Artifacts**: Stored in S3 for version control

### 5. Data Storage Layer
- **Amazon S3**: Multiple prefixes for different data stages
  - `initial_dataset/`: Raw input data
  - `retrieved_from_db/`: Data extracted from database
  - `input_batch/`: Prepared for ML inference
  - `output_batch/`: ML prediction results
  - `predicted_values_output/`: Final processed results
  - `batch_job_metadata/`: Job tracking information
- **Aurora PostgreSQL**: Stores sensor data and prediction results
- **AWS Secrets Manager**: Securely manages database credentials

### 6. Security & Access Control
- **IAM Roles**: Least privilege access for each component
  - DB Init Role: Database setup permissions
  - DB Reader Role: Read-only database access
  - DB Writer Role: Read-write database access
  - Batch Initiate Role: SageMaker job creation and S3 input permissions
  - Batch Callback Role: S3 output processing and Step Functions callback permissions
  - Step Functions Role: Orchestration permissions
  - Scheduler Role: EventBridge permissions

### 7. Network Architecture
- **VPC**: Isolated network environment
- **Public Subnets**: NAT Gateway for outbound internet access
- **Private Subnets**: All compute and database resources
- **Security Groups**: Fine-grained network access control

### 8. Monitoring & Metadata
- **CloudWatch Logs**: Centralized logging for all components
- **CloudWatch Metrics**: Performance and health monitoring
- **Parameter Store**: Stores batch job metadata and configuration

## Data Flow Process

1. **Initialization**: CSV data is uploaded to S3, database is initialized with schema and initial data
2. **Scheduled Trigger**: EventBridge Scheduler triggers Step Functions every 24 hours
3. **Data Query**: Lambda function queries database for new records matching the configured parameter (PM 2.5, PM 10, or PM 1)
4. **Conditional Processing**: If records are found, proceed with ML inference; otherwise, end workflow
5. **Batch Transform Initiation**: InitiateBatchTransform Lambda creates SageMaker batch job and stores task token
6. **Step Functions Wait**: Step Functions enters WAIT_FOR_TASK_TOKEN state
7. **EventBridge Monitoring**: EventBridge monitors SageMaker job completion events
8. **Callback Trigger**: When job completes, EventBridge triggers BatchTransformCallback Lambda
9. **Task Token Callback**: Callback Lambda sends success/failure back to Step Functions using stored task token
10. **Result Storage**: Step Functions resumes and writes predictions to database with `predicted_label = true`
11. **Completion**: Workflow ends, ready for next scheduled execution

## Key Features

- **Configurable Parameter Selection**: Users can choose which air quality parameter to predict
- **Scalable Architecture**: Handles large datasets through batch processing
- **Fault Tolerant**: Step Functions provide retry logic and error handling
- **Secure**: All data encrypted at rest and in transit, least privilege access
- **Cost Optimized**: Serverless architecture scales to zero when not in use
- **Monitored**: Comprehensive logging and metrics for operational visibility

## Timeout Configuration

### Step Functions
- **Overall State Machine**: 2 hours maximum execution time
- **Individual Steps**: 1 hour timeout each (Query, Batch Transform, Write Results)

### Lambda Functions
- **Initiate Batch Transform Lambda**: 15 minutes (complex data processing)
- **Other Lambda Functions**: 2 minutes (standard operations)

## Error Handling

The system includes comprehensive error handling:
- **Timeout States**: Specific failure states for timeout scenarios
- **Error Catching**: All Lambda tasks have explicit error handling
- **Failure Callbacks**: Proper Step Functions failure notifications
- **Status Code Handling**: HTTP 400+ errors transition to failed states
