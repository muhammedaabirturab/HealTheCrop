# UML Diagrams

## Use Case Diagram

```mermaid
flowchart LR
    Farmer((Farmer))
    Admin((Admin))
    ESP32((ESP32 Device))

    subgraph HealTheCrop
        UC1([Register / Login])
        UC2([View Dashboard])
        UC3([Enter Manual Soil Data])
        UC4([Get Crop Recommendation])
        UC5([Scan Crop for Pests/Disease])
        UC6([View Fertility Suggestions])
        UC7([View History])
        UC8([Switch Language])
        UC9([Ingest Sensor Reading])
        UC10([Manage Users/Devices])
    end

    Farmer --> UC1
    Farmer --> UC2
    Farmer --> UC3
    Farmer --> UC4
    Farmer --> UC5
    Farmer --> UC6
    Farmer --> UC7
    Farmer --> UC8
    ESP32 --> UC9
    Admin --> UC10
    UC4 -.includes.-> UC3
    UC6 -.includes.-> UC2
```

## Class Diagram (core domain model)

```mermaid
classDiagram
    class User {
        +int id
        +string name
        +string email
        +string hashed_password
        +string role
        +string preferred_language
        +verify_password()
    }
    class Device {
        +int id
        +string device_uid
        +string status
        +datetime last_seen
    }
    class SensorReading {
        +int id
        +float nitrogen
        +float phosphorus
        +float potassium
        +float moisture
        +float temperature
        +float humidity
        +float ph
        +float rainfall
    }
    class Prediction {
        +int id
        +dict input_features
        +string recommended_crop
        +float confidence
        +list alternatives
    }
    class PestDetection {
        +int id
        +string image_key
        +list detections
        +string model_used
    }
    class FertilityReport {
        +int id
        +float fertility_score
        +list issues
        +list suggestions
    }
    class CropPredictor {
        +predict(features, season, location) dict
        +get_crop_details(crop) dict
    }
    class DiseaseDetectionService {
        +detect(image_bytes) dict
        -_predict_cnn(image) list
        -_predict_heuristic(image) list
    }

    User "1" --> "many" Device : owns
    User "1" --> "many" Prediction : makes
    User "1" --> "many" PestDetection : uploads
    User "1" --> "many" FertilityReport : requests
    Device "1" --> "many" SensorReading : produces
    Prediction ..> CropPredictor : uses
    PestDetection ..> DiseaseDetectionService : uses
```

## Sequence Diagram — Manual Crop Recommendation

```mermaid
sequenceDiagram
    actor Farmer
    participant UI as React Frontend
    participant API as FastAPI /predictions/manual
    participant Season as Season Resolver
    participant ML as CropPredictor
    participant DB as Database

    Farmer->>UI: Enter N,P,K,temp,humidity,pH,rainfall
    UI->>API: POST /predictions/manual (JWT)
    API->>Season: resolve_season(manual_override)
    Season-->>API: season string
    API->>ML: predict(features, season, location)
    ML-->>API: {crop, confidence, alternatives, importance}
    API->>DB: INSERT prediction record
    DB-->>API: record id
    API-->>UI: PredictionResponse (200)
    UI-->>Farmer: Crop cards rendered
```

## Sequence Diagram — Pest Scan

```mermaid
sequenceDiagram
    actor Farmer
    participant UI as React Frontend
    participant API as FastAPI /pest/scan
    participant CV as DiseaseDetectionService
    participant Storage as MinIO / Local Disk
    participant DB as Database

    Farmer->>UI: Upload leaf photo
    UI->>API: POST /pest/scan (multipart, JWT)
    API->>API: validate content-type & size
    API->>CV: detect(image_bytes)
    alt trained CNN available
        CV->>CV: MobileNetV2 inference
    else fallback
        CV->>CV: OpenCV color/blob heuristic
    end
    CV-->>API: detections + severity
    API->>Storage: upload_bytes(image)
    Storage-->>API: object key
    API->>DB: INSERT pest_detection
    API-->>UI: PestDetectionResponse (200)
    UI-->>Farmer: Treatment cards rendered
```

## Activity Diagram — Fertility Improvement Flow

```mermaid
flowchart TD
    Start([Sensor reading or manual input received])
    Compute[Compute soil health indicators\n& fertility score]
    Check{Fertility score\n< 75?}
    Flag[Flag low N/P/K, pH extremes,\nmoisture extremes]
    Lookup[Look up matching\nfertility_recommendations.json entries]
    Suggest[Return suggestions:\nwhy / how / improvement / time]
    NoAction[No suggestions needed]
    End([Display on Dashboard])

    Start --> Compute --> Check
    Check -->|yes| Flag --> Lookup --> Suggest --> End
    Check -->|no| NoAction --> End
```
