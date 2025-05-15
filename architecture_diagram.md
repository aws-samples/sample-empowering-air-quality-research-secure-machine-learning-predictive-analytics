# Air Quality Monitoring System Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        Air Quality Monitoring System               │
│                                                                    │
│  ┌──────────────┐    ┌───────────────┐    ┌────────────────────┐   │
│  │              │    │   EventBridge │    │   Step Functions   |   │
│  │ Air Quality  │    │   Scheduler   │──▶│   State Machine     │   │
│  │   Sensors    │    │               │    │                    │   │
│  │              │    └───────────────┘    └────────────┬───────┘   │
│  └──────┬───────┘                                      │           │
│         │                                              ▼           │
│         │                                   ┌────────────────────┐ │
│         ▼                                   │                    │ │
│  ┌──────────────┐                           │   Lambda Functions │ │
│  │              │      ┌───────────────┐    │   - Data Processing│ │
│  │     S3       │      │   SageMaker   │    │   - DB Operations  │ │
│  │   Bucket     │─────▶│   Endpoint    │◀───│   - ML Inference   │ │
│  │              │      │               │    │                    │ │
│  └──────────────┘      └───────────────┘    └────────┬───────────┘ │
│         ▲                      │                      │            │
│         │                      │                      │            │
│         │                      ▼                      ▼            │
│  ┌──────────────────────────────────────────────────────────-┐     │
│  │                      Amazon RDS                           │     │
│  │                   PostgreSQL Database                     │     │
│  │                                                           │     │
│  └──────────────────────────────────────────────────────────-┘     │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Data Flow

1. **Data Ingestion**:
   - Air quality sensor data is collected and stored in S3 buckets
   - EventBridge scheduler triggers the data processing workflow at regular intervals

2. **Processing Pipeline**:
   - Step Functions orchestrate the entire workflow
   - Lambda functions process the raw data and prepare it for inference
   - SageMaker endpoint runs the ML model for air quality predictions
   - Results are stored in the PostgreSQL database

3. **Data Storage**:
   - Raw sensor data is stored in S3
   - Processed data and predictions are stored in RDS PostgreSQL
   - Model artifacts are stored in S3

4. **Network Architecture**:
   - All components run within a VPC
   - Database is in private subnets
   - Lambda functions use VPC endpoints for secure access
   - NAT Gateway enables outbound internet access from private subnets

### AWS Services Used

- **Compute**: AWS Lambda
- **Orchestration**: AWS Step Functions, EventBridge
- **Storage**: Amazon S3, Amazon RDS (PostgreSQL)
- **Machine Learning**: Amazon SageMaker
- **Networking**: Amazon VPC, Security Groups, NAT Gateway
- **Security**: IAM Roles, AWS Secrets Manager
- **Monitoring**: CloudWatch Logs, CloudWatch Metrics

### Security Considerations

- All data is encrypted at rest and in transit
- Least privilege IAM roles for all components
- Network isolation through VPC design
- Database credentials managed through Secrets Manager
