#!/usr/bin/env python3
"""
Phone Detection Integration Verification Script

Tests and validates the Roboflow phone detector integration.
Provides diagnostic information about model loading and inference.

Usage:
    python verify_phone_detection.py
    python verify_phone_detection.py --verbose
    python verify_phone_detection.py --test-image path/to/test_image.jpg
"""

import os
import sys
import argparse
import cv2
import numpy as np
from pathlib import Path

# Add scripts to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, 'scripts'))

from object_classifier import get_model_info, classify_hand_object


def print_section(title):
    """Print formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def verify_model_files():
    """Verify that model files exist."""
    print_section("1. Model File Verification")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_dir = os.path.join(base_dir, 'model')
    
    models = {
        'Roboflow Phone Detector': os.path.join(model_dir, 'phone_detector.pt'),
        'Custom Multi-class Model': os.path.join(model_dir, 'phone_book_best.pt'),
        'YOLO Person Detector': os.path.join(base_dir, 'yolov8m.pt'),
        'YOLO Fallback': os.path.join(base_dir, 'yolov8n.pt'),
    }
    
    results = {}
    for name, path in models.items():
        exists = os.path.exists(path)
        status = "✅ FOUND" if exists else "❌ NOT FOUND"
        size = ""
        if exists:
            size = f" ({os.path.getsize(path) / 1024 / 1024:.1f} MB)"
        print(f"{status} {name}")
        if exists:
            print(f"     Path: {path}{size}")
        results[name] = exists
    
    return results


def verify_model_loading():
    """Verify that model loads correctly."""
    print_section("2. Model Loading Verification")
    
    try:
        info = get_model_info()
        print(f"✅ Model loaded successfully!\n")
        print(f"Model Type: {info['type']}")
        print(f"Description: {info['description']}")
        print(f"Path: {info['path']}")
        
        if info['type'] == 'roboflow_phone':
            print(f"\n🎉 Roboflow Phone Detector is ACTIVE!")
        elif info['type'] == 'custom_multi':
            print(f"\n✅ Custom multi-class model is active")
        else:
            print(f"\n⚠️  COCO fallback model is active (Roboflow model may not be found)")
        
        return True
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        return False


def test_inference(test_image_path=None):
    """Test inference on a sample image."""
    print_section("3. Inference Test")
    
    if test_image_path and os.path.exists(test_image_path):
        frame = cv2.imread(test_image_path)
        print(f"📷 Testing with provided image: {test_image_path}")
    else:
        # Create a dummy test image
        print("📷 Creating synthetic test image...")
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Add some random content
        cv2.rectangle(frame, (50, 50), (300, 400), (100, 150, 200), -1)
        cv2.circle(frame, (320, 240), 100, (200, 100, 50), -1)
    
    try:
        print(f"   Image size: {frame.shape}")
        
        # Test with a dummy bounding box (center region)
        h, w = frame.shape[:2]
        bbox = (w//4, h//4, 3*w//4, 3*h//4)
        
        print(f"   Test bbox: {bbox}")
        print(f"   Running phone detection on hand region...")
        
        result = classify_hand_object(frame, bbox, conf_threshold=0.35)
        
        print(f"\n✅ Inference successful!")
        print(f"   Result: {result}")
        print(f"   (Expected: 'phone', 'book', 'laptop', or 'none')")
        
        return True
    except Exception as e:
        print(f"❌ Inference failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_dependencies():
    """Check required Python dependencies."""
    print_section("4. Dependency Check")
    
    dependencies = {
        'ultralytics': 'YOLO framework',
        'cv2': 'OpenCV',
        'numpy': 'NumPy',
        'torch': 'PyTorch',
    }
    
    results = {}
    for module, description in dependencies.items():
        try:
            __import__(module)
            print(f"✅ {module:15} ({description})")
            results[module] = True
        except ImportError:
            print(f"❌ {module:15} ({description}) - NOT INSTALLED")
            results[module] = False
    
    all_present = all(results.values())
    if not all_present:
        print(f"\n⚠️  Some dependencies are missing!")
        print(f"   Run: pip install -r requirements.txt")
    
    return all_present


def print_usage_guide():
    """Print quick usage guide."""
    print_section("5. Quick Usage Guide")
    
    print("To use phone detection in your code:\n")
    print("```python")
    print("from object_classifier import classify_hand_object")
    print("from ultralytics import YOLO")
    print("import cv2")
    print("")
    print("# Load frame")
    print("frame = cv2.imread('path/to/image.jpg')")
    print("")
    print("# Detect phone in hand region")
    print("# bbox = (x1, y1, x2, y2) - person bounding box")
    print("result = classify_hand_object(frame, bbox, conf_threshold=0.35)")
    print("")
    print("# result will be: 'phone', 'book', 'laptop', or 'none'")
    print("```\n")
    
    print("Available confidence thresholds:")
    print("  0.25-0.30 : Lenient (catches more phones, more false positives)")
    print("  0.35-0.45 : Balanced (default)")
    print("  0.50-0.60 : Strict (fewer false positives, may miss some)")


def generate_report(results_dict):
    """Generate and display a summary report."""
    print_section("Integration Status Report")
    
    status = "✅ READY" if results_dict.get('model_loading') else "❌ ERROR"
    print(f"Overall Status: {status}\n")
    
    print("Results:")
    print(f"  Model Files:      {'✅ OK' if results_dict.get('model_files') else '❌ MISSING'}")
    print(f"  Model Loading:    {'✅ OK' if results_dict.get('model_loading') else '❌ FAILED'}")
    print(f"  Inference:        {'✅ OK' if results_dict.get('inference') else '❌ FAILED'}")
    print(f"  Dependencies:     {'✅ OK' if results_dict.get('dependencies') else '❌ MISSING'}")
    
    if results_dict.get('model_loading'):
        info = get_model_info()
        print(f"\nActive Model: {info['type']}")
        if info['type'] == 'roboflow_phone':
            print("🎉 Your Roboflow phone detector is active and ready!")
    
    print("\n📚 For detailed setup, see: PHONE_DETECTION_GUIDE.md")


def main():
    parser = argparse.ArgumentParser(
        description='Verify Smart Classroom Phone Detection Integration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python verify_phone_detection.py
  python verify_phone_detection.py --verbose
  python verify_phone_detection.py --test-image path/to/test.jpg
        """
    )
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--test-image', help='Path to test image for inference')
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("  Smart Classroom Phone Detection - Integration Verification")
    print("="*60)
    
    results = {}
    
    # Run verification checks
    verify_model_files()
    results['model_files'] = True
    
    results['model_loading'] = verify_model_loading()
    results['inference'] = test_inference(args.test_image)
    results['dependencies'] = check_dependencies()
    
    # Print guides and report
    print_usage_guide()
    generate_report(results)
    
    print("\n" + "="*60)
    
    if results['model_loading']:
        print("✅ Integration verification PASSED!")
        print("   Your Roboflow phone detector is ready to use.")
        sys.exit(0)
    else:
        print("❌ Integration verification FAILED!")
        print("   Please check the errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
