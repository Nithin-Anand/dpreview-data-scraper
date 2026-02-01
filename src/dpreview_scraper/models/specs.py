"""Camera specifications model."""

from typing import List
from pydantic import BaseModel, Field


class CameraSpecs(BaseModel):
    """Camera technical specifications matching DPReview schema."""

    # Exposure & Metering
    AEBracketing: str = ""
    AperturePriority: str = ""
    ExposureCompensation: str = ""
    ExposureModes: List[str] = Field(default_factory=list)
    ManualExposureMode: str = ""
    MeteringModes: List[str] = Field(default_factory=list)
    ShutterPriority: str = ""

    # Dates & Pricing
    Announced: str = ""
    BuyingOptions: str = ""
    MSRP: str = ""

    # Autofocus
    Autofocus: List[str] = Field(default_factory=list)
    AutofocusAssistLamp: str = ""
    NumberOfFocusPoints: str = ""

    # Battery
    Battery: str = ""
    BatteryDescription: str = ""
    BatteryLifeCIPA: str = ""

    # Body & Build
    BodyMaterial: str = ""
    BodyType: str = ""
    Dimensions: str = ""
    Durability: str = ""
    EnvironmentallySealed: str = ""
    WeightIncBatteries: str = ""

    # ISO
    BoostedISOMaximum: str = ""
    BoostedISOMinimum: str = ""
    ISO: str = ""

    # Flash
    BuiltInFlash: str = ""
    ExternalFlash: str = ""
    FlashModes: str = ""
    FlashRange: str = ""
    FlashXSyncSpeed: str = ""

    # Image
    ColorFilterArray: str = ""
    ColorSpace: str = ""
    CustomWhiteBalance: str = ""
    EffectivePixels: str = ""
    FileFormat: List[str] = Field(default_factory=list)
    ImageRatioWh: str = ""
    JPEGQualityLevels: str = ""
    MaxResolution: str = ""
    OtherResolutions: str = ""
    UncompressedFormat: str = ""
    WBBracketing: str = ""
    WhiteBalancePresets: str = ""

    # Sensor
    FocalLengthMultiplier: str = ""
    Processor: str = ""
    SensorPhotoDetectors: str = ""
    SensorSize: str = ""
    SensorType: str = ""

    # Shutter
    MaximumShutterSpeed: str = ""
    MaximumShutterSpeedElectronic: str = ""
    MinimumShutterSpeed: str = ""

    # Screen
    ArticulatedLCD: str = ""
    ScreenDots: str = ""
    ScreenSize: str = ""
    ScreenType: str = ""
    TouchScreen: str = ""

    # Viewfinder
    FieldOfView: str = ""
    ViewfinderCoverage: str = ""
    ViewfinderMagnification: str = ""
    ViewfinderResolution: str = ""
    ViewfinderType: str = ""

    # Video
    Format: str = ""
    Microphone: str = ""
    MicrophonePort: str = ""
    Modes: List[str] = Field(default_factory=list)
    Resolutions: str = ""
    Speaker: str = ""
    HeadphonePort: str = ""
    TimelapseRecording: str = ""

    # Connectivity
    GPS: str = ""
    GPSNotes: str = ""
    HDMI: str = ""
    RemoteControl: str = ""
    USB: str = ""
    USBCharging: str = ""
    Wireless: str = ""
    WirelessNotes: str = ""

    # Shooting
    CIPAImageStabilizationRating: str = ""
    ContinuousDrive: str = ""
    DriveModes: str = ""
    ImageStabilization: str = ""
    ImageStabilizationNotes: str = ""
    LiveView: str = ""
    ManualFocus: str = ""
    OrientationSensor: str = ""
    SelfTimer: str = ""

    # Lens
    LensMount: str = ""
    NumberOfLenses: str = ""

    # Storage
    StorageTypes: str = ""

    # Modes
    DigitalZoom: str = ""
    SceneModes: str = ""
    SubjectSceneModes: str = ""

    # Review metadata (appears in some samples)
    ReviewPreview: str = ""

    class Config:
        extra = "allow"  # Allow unknown fields from DPReview
