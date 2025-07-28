# Air Quality ML-Driven Predictive Analytics Architecture

## System Architecture Diagram

```mermaid
graph TD
    EventBridge[EventBridge Scheduler] -->|Triggers every 24h| StepFunctions[AWS Step Functions]
    
    StepFunctions -->|1- Start workflow| QueryLambda[Query Lambda]
    QueryLambda -->|2- Retrieve records| RDS[(Aurora PostgreSQL)]
    QueryLambda -->|3- Store data| S3_Retrieved[S3 - retrieved_from_db]
    
    StepFunctions -->|4- Check if records available| Choice{Records Available?}
    Choice -->|No| End[No Records Found]
    Choice -->|Yes| BatchTransformLambda[Initiate Batch Transform Lambda]
    
    BatchTransformLambda -->|5- Read data| S3_Retrieved
    BatchTransformLambda -->|6- Prepare input| S3_Input[S3 - input_batch]
    BatchTransformLambda -->|7- Start job| SageMaker[SageMaker Batch Transform]
    BatchTransformLambda -->|8- Store job metadata| SSM[SSM Parameter Store]
    
    SageMaker -->|9- Process data| S3_Input
    SageMaker -->|10- Store results| S3_Output[S3 - output_batch]
    
    SageMaker -->|11- Job completion event| EventBridgeRule[EventBridge Rule]
    EventBridgeRule -->|12- Trigger callback| CallbackLambda[Batch Transform Callback Lambda]
    
    CallbackLambda -->|13- Read job metadata| SSM
    CallbackLambda -->|14- Read results| S3_Output
    CallbackLambda -->|15- Process results| S3_Predicted[S3 - predicted_values_output]
    CallbackLambda -->|16- Send success/failure| StepFunctions
    
    StepFunctions -->|17- If successful| WriterLambda[Write Results Lambda]
    WriterLambda -->|18- Read predictions| S3_Predicted
    WriterLambda -->|19- Write to database| RDS
    WriterLambda -->|20- Complete workflow| StepFunctions
    
    classDef aws fill:#FF9900,stroke:#232F3E,color:#232F3E
    classDef lambda fill:#FF9900,stroke:#232F3E,color:#232F3E
    classDef database fill:#3B48CC,stroke:#232F3E,color:white
    classDef storage fill:#277116,stroke:#232F3E,color:white
    classDef control fill:#CC2264,stroke:#232F3E,color:white
    
    class EventBridge,EventBridgeRule,StepFunctions,SageMaker,SSM aws
    class QueryLambda,BatchTransformLambda,CallbackLambda,WriterLambda lambda
    class RDS database
    class S3_Retrieved,S3_Input,S3_Output,S3_Predicted storage
    class Choice,End control
```

## Data Flow Diagram

```mermaid
graph LR
    DB[(Aurora PostgreSQL)]
    S3[S3 Bucket]
    
    RawData[Raw Air Quality Data] -->|1- Initial Load| DB
    DB -->|2- Query missing values| QueryData[Data with Missing Values]
    QueryData -->|3- Store CSV| S3
    S3 -->|4- Batch transform input| MLInput[ML Input Data]
    MLInput -->|5- Process| MLModel[SageMaker Model]
    MLModel -->|6- Generate predictions| Predictions[Predicted Values]
    Predictions -->|7- Store results| S3
    S3 -->|8- Read predictions| ProcessedData[Processed Data]
    ProcessedData -->|9- Update database| DB
    
    classDef data fill:#3B48CC,stroke:#232F3E,color:white
    classDef process fill:#FF9900,stroke:#232F3E,color:#232F3E
    classDef storage fill:#277116,stroke:#232F3E,color:white
    
    class RawData,QueryData,MLInput,Predictions,ProcessedData data
    class MLModel process
    class DB,S3 storage
```

## Component Interaction Sequence

```mermaid
sequenceDiagram
    participant Scheduler as EventBridge Scheduler
    participant StepFn as Step Functions
    participant QueryLambda as Query Lambda
    participant DB as Aurora PostgreSQL
    participant S3 as S3 Bucket
    participant BatchLambda as Batch Transform Lambda
    participant SageMaker as SageMaker
    participant EventRule as EventBridge Rule
    participant CallbackLambda as Callback Lambda
    participant WriterLambda as Writer Lambda
    
    Scheduler->>StepFn: Trigger workflow (every 24h)
    
    StepFn->>QueryLambda: Start query
    QueryLambda->>DB: Query records with missing values
    DB-->>QueryLambda: Return records
    QueryLambda->>S3: Store data in retrieved_from_db/
    QueryLambda-->>StepFn: Return status
    
    alt No records found
        StepFn->>StepFn: End workflow
    else Records found
        StepFn->>BatchLambda: Start batch transform
        BatchLambda->>S3: Read data from retrieved_from_db/
        BatchLambda->>S3: Prepare and store in input_batch/
        BatchLambda->>SageMaker: Create batch transform job
        BatchLambda->>SSM: Store job metadata
        BatchLambda-->>StepFn: Return task token
        
        SageMaker->>S3: Read input data
        SageMaker->>SageMaker: Process data
        SageMaker->>S3: Write results to output_batch/
        SageMaker-->>EventRule: Job completion event
        
        EventRule->>CallbackLambda: Trigger callback
        CallbackLambda->>SSM: Get job metadata
        CallbackLambda->>S3: Read batch results
        CallbackLambda->>S3: Process and store in predicted_values_output/
        CallbackLambda-->>StepFn: Send task success/failure
        
        StepFn->>WriterLambda: Write results to DB
        WriterLambda->>S3: Read from predicted_values_output/
        WriterLambda->>DB: Update records with predictions
        WriterLambda-->>StepFn: Return status
    end
    
    StepFn-->>Scheduler: Workflow complete
```

## Infrastructure Stack Diagram

```mermaid
graph TD
    MainStack[Main Stack] --> NetworkStack[Network Stack]
    MainStack --> DatabaseStack[Database Stack]
    MainStack --> StorageStack[Storage Stack]
    MainStack --> SageMakerStack[SageMaker Stack]
    MainStack --> LambdaStack[Lambda Stack]
    MainStack --> StepFunctionsStack[Step Functions Stack]
    MainStack --> EventBridgeStack[EventBridge Scheduler Stack]
    
    NetworkStack --> VPC[VPC]
    NetworkStack --> SecurityGroups[Security Groups]
    
    DatabaseStack --> Aurora[Aurora PostgreSQL]
    DatabaseStack --> DBSecrets[DB Credentials Secret]
    
    StorageStack --> S3Bucket[S3 Bucket]
    
    SageMakerStack --> CanvasModel[Canvas Model]
    SageMakerStack --> BatchTransformModel[Batch Transform Model]
    
    LambdaStack --> DBInitLambda[DB Init Lambda]
    LambdaStack --> QueryLambda[Query Lambda]
    LambdaStack --> BatchTransformLambda[Batch Transform Lambda]
    LambdaStack --> CallbackLambda[Callback Lambda]
    LambdaStack --> WriterLambda[Writer Lambda]
    LambdaStack --> IAMRoles[IAM Roles]
    
    StepFunctionsStack --> StateMachine[State Machine]
    
    EventBridgeStack --> Scheduler[EventBridge Scheduler]
    
    classDef stack fill:#232F3E,stroke:#FF9900,color:white
    classDef network fill:#3B48CC,stroke:#232F3E,color:white
    classDef database fill:#3B48CC,stroke:#232F3E,color:white
    classDef storage fill:#277116,stroke:#232F3E,color:white
    classDef compute fill:#FF9900,stroke:#232F3E,color:#232F3E
    classDef orchestration fill:#CC2264,stroke:#232F3E,color:white
    classDef security fill:#7AA116,stroke:#232F3E,color:white
    
    class MainStack,NetworkStack,DatabaseStack,StorageStack,SageMakerStack,LambdaStack,StepFunctionsStack,EventBridgeStack stack
    class VPC,SecurityGroups network
    class Aurora,DBSecrets database
    class S3Bucket storage
    class CanvasModel,BatchTransformModel,DBInitLambda,QueryLambda,BatchTransformLambda,CallbackLambda,WriterLambda compute
    class StateMachine,Scheduler orchestration
    class IAMRoles security
