#!/usr/bin/env python3
"""
WattWatch - Main entry point for intelligent occupancy detection.

Usage:
    python main.py detect <video_path>     # Process video file
    python main.py live                     # Process webcam feed
    python main.py benchmark                # Run on test clips
"""

import argparse
import sys
import time
from pathlib import Path
import cv2

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.detector import YOLODetector
from src.tracker import create_tracker
from src.utils import FPSCounter, VideoFrameExtractor, JSONLogger
from src.appliance_status import ApplianceStatusRecognizer
from src.intensity_calibrator import IntensityCalibrator, create_calibrator


def load_config():
    """Load configuration from config.yaml"""
    import yaml
    
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return {}


def cmd_detect(args, config):
    """Run detection on video or image."""
    print(f"Running detection on: {args.input}")
    
    # Initialize detector
    conf_threshold = args.confidence if args.confidence else config.get("detection", {}).get("min_confidence", 0.3)
    detector = YOLODetector(
        model_name=config.get("model", {}).get("name", "yolov8n.pt"),
        confidence_threshold=conf_threshold,
        device=config.get("device", {}).get("type")
    )
    
    print("Loading YOLOv8 model...")
    detector.load_model()
    
    # Initialize utilities
    fps_counter = FPSCounter()
    logger = JSONLogger(config.get("logging", {}).get("detection_log_file", "output/detections.json"))
    tracker = create_tracker(
        max_distance=config.get("tracking", {}).get("max_distance", 60.0),
        max_frames_to_skip=config.get("tracking", {}).get("max_frames_to_skip", 25)
    )
    
    # Setup FPS log file
    fps_log_path = Path(config.get("logging", {}).get("fps_log_file", "logs/fps.log"))
    fps_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize appliance recognizer if enabled
    appliance_config = config.get("appliance", {})
    appliance_recognizer = None
    appliance_results = {"light": [], "ceiling_fan": []}
    
    if appliance_config.get("enabled", False):
        try:
            appliance_recognizer = ApplianceStatusRecognizer()
            print("Appliance status recognition initialized")
        except Exception as e:
            print(f"Warning: Could not initialize appliance recognizer: {e}")
    
    # Check if input is video or image
    input_path = Path(args.input)
    if input_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
        # Single image
        import cv2
        frame = cv2.imread(str(input_path))
        if frame is None:
            print(f"Error: Could not read image {input_path}")
            return 1
        
        detections = detector.detect_people(frame)
        count = len(detections)
        
        print(f"Detected {count} people in image")
        
        if args.output:
            from src.utils import draw_detections
            output_frame = draw_detections(frame, detections)
            cv2.imwrite(args.output, output_frame)
            print(f"Output saved to: {args.output}")
        
        return 0
    
    # Video or camera
    extractor = VideoFrameExtractor(args.input)
    if not extractor.open():
        print(f"Error: Could not open video source: {args.input}")
        return 1
    
    print(f"Video info: {extractor.width}x{extractor.height} @ {extractor.fps} fps, {extractor.total_frames} frames")
    
    # Create output directory
    output_dir = Path(config.get("paths", {}).get("output_dir", "output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process video with try/finally for clean shutdown
    frame_index = 0
    total_count = 0
    max_people = 0
    start_time = time.time()
    
    print("Processing video... (press Ctrl+C to stop)")
    
    try:
        while True:
            frame = extractor.read_frame()
            if frame is None:
                break
            
            # Skip frames if configured
            frame_skip = config.get("detection", {}).get("frame_skip", 1)
            if frame_index % frame_skip != 0:
                frame_index += 1
                continue
            
            # Detect people
            detections = detector.detect_people(frame)
            tracked_detections, unique_count = tracker.track(detections)
            count = len(detections)
            total_count += count
            max_people = max(max_people, unique_count)
            
            # Update FPS
            fps_counter.update()
            current_fps = fps_counter.get_fps()
            avg_fps = fps_counter.get_average_fps()
            
            # Log results to JSON
            logger.log_frame(frame_index, count, detections, current_fps)
            
            # Log FPS to file
            log_interval = config.get("logging", {}).get("log_interval", 30)
            if frame_index % log_interval == 0:
                with open(fps_log_path, "a") as f:
                    f.write(f"frame={frame_index},fps={current_fps:.2f},avg_fps={avg_fps:.2f},count={count}\n")
            
            # Print progress
            if frame_index % 30 == 0:
                print(f"Frame {frame_index}: {count} people, unique: {unique_count}, FPS: {current_fps:.1f}, Avg: {avg_fps:.1f}")
            
            # Detect appliance status (less frequent)
            if appliance_recognizer and frame_index % appliance_config.get("frame_skip", 10) == 0:
                try:
                    appliance_statuses = appliance_recognizer.detect_all_appliances(frame)
                    for status in appliance_statuses:
                        if status.appliance_type.value == "light":
                            appliance_results["light"].append({
                                "frame": frame_index,
                                "status": status.status.value,
                                "confidence": status.confidence
                            })
                            print(f"  -> Light: {status.status.value} (conf: {status.confidence:.2f})")
                        elif status.appliance_type.value == "ceiling_fan":
                            appliance_results["ceiling_fan"].append({
                                "frame": frame_index,
                                "status": status.status.value,
                                "confidence": status.confidence
                            })
                            print(f"  -> Ceiling Fan: {status.status.value} (conf: {status.confidence:.2f})")
                except Exception as e:
                    print(f"  -> Appliance detection error: {e}")
            
            # Save frame with detections if output enabled
            if args.output and frame_index % 100 == 0:
                from src.utils import draw_detections
                output_frame = draw_detections(frame, detections)
                cv2.imwrite(str(output_dir / f"frame_{frame_index:05d}.jpg"), output_frame)
            
            frame_index += 1
            
            # Limit frames if specified
            if args.max_frames and frame_index >= args.max_frames:
                break
                
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    finally:
        # Cleanup
        extractor.release()
        logger.save()
    
    # Print summary
    elapsed = time.time() - start_time
    print(f"\nProcessing complete!")
    print(f"Total frames: {frame_index}")
    print(f"Total detections (sum per frame): {total_count}")
    print(f"Peak unique people at any time: {max_people}")
    print(f"Average FPS: {fps_counter.get_average_fps():.1f}")
    print(f"Elapsed time: {elapsed:.1f}s")
    print(f"Results saved to: {logger.output_path}")
    print(f"FPS log saved to: {fps_log_path}")
    
    # Print appliance detection summary
    if appliance_recognizer:
        print("\n--- Appliance Status Summary ---")
        for appliance_type, results in appliance_results.items():
            if results:
                on_count = sum(1 for r in results if r["status"] == "ON")
                off_count = sum(1 for r in results if r["status"] == "OFF")
                print(f"{appliance_type}: ON={on_count}, OFF={off_count}, frames={len(results)}")
            else:
                print(f"{appliance_type}: No detections")
        
        # Save appliance results
        import json
        appliance_output_path = output_dir / "appliance_status.json"
        with open(appliance_output_path, "w") as f:
            json.dump(appliance_results, f, indent=2)
        print(f"Appliance results saved to: {appliance_output_path}")
    
    return 0


def cmd_live(args, config):
    """Run detection on live camera feed."""
    print(f"Starting live detection from camera: {args.camera}")
    
    # Initialize detector
    detector = YOLODetector(
        model_name=config.get("model", {}).get("name", "yolov8n.pt"),
        confidence_threshold=config.get("detection", {}).get("min_confidence", 0.3),
        device=config.get("device", {}).get("type")
    )
    
    print("Loading YOLOv8 model...")
    detector.load_model()
    
    # Initialize video capture
    extractor = VideoFrameExtractor(str(args.camera))
    if not extractor.open():
        print(f"Error: Could not open camera: {args.camera}")
        return 1
    
    fps_counter = FPSCounter()
    
    print("Press 'q' to quit")
    
    while True:
        frame = extractor.read_frame()
        if frame is None:
            break
        
        # Detect people
        detections = detector.detect_people(frame)
        count = len(detections)
        
        # Update FPS
        fps_counter.update()
        
        # Draw detections on frame
        from src.utils import draw_detections
        output_frame = draw_detections(frame, detections)
        
        # Add info overlay
        cv2.putText(output_frame, f"People: {count}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(output_frame, f"FPS: {fps_counter.get_fps():.1f}", (10, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Display
        cv2.imshow("WattWatch - Live Detection", output_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    extractor.release()
    cv2.destroyAllWindows()
    
    print(f"\nAverage FPS: {fps_counter.get_average_fps():.1f}")
    return 0


def cmd_benchmark(args, config):
    """Run benchmark on test clips."""
    print("Running benchmark on test clips...")
    
    test_clips = config.get("test_clips", {})
    
    if not test_clips:
        print("Error: No test clips configured in config.yaml")
        return 1
    
    # Initialize detector
    detector = YOLODetector(
        model_name=config.get("model", {}).get("name", "yolov8n.pt"),
        confidence_threshold=config.get("detection", {}).get("min_confidence", 0.3),
        device=config.get("device", {}).get("type")
    )
    
    print("Loading YOLOv8 model...")
    detector.load_model()
    
    results = {}
    
    for clip_name, clip_path in test_clips.items():
        print(f"\n--- Testing: {clip_name} ---")
        print(f"Path: {clip_path}")
        
        path = Path(clip_path)
        if not path.exists():
            print(f"Warning: Clip not found: {clip_path}")
            results[clip_name] = {"status": "missing", "path": clip_path}
            continue
        
        # Process clip
        extractor = VideoFrameExtractor(str(path))
        if not extractor.open():
            print(f"Error: Could not open clip: {clip_path}")
            results[clip_name] = {"status": "error", "path": clip_path}
            continue
        
        fps_counter = FPSCounter()
        frame_count = 0
        total_detections = 0
        max_count = 0
        min_count = float('inf')
        
        while True:
            frame = extractor.read_frame()
            if frame is None:
                break
            
            detections = detector.detect_people(frame)
            count = len(detections)
            
            fps_counter.update()
            frame_count += 1
            total_detections += count
            max_count = max(max_count, count)
            min_count = min(min_count, count)
        
        extractor.release()
        
        avg_fps = fps_counter.get_average_fps()
        avg_count = total_detections / frame_count if frame_count > 0 else 0
        
        results[clip_name] = {
            "status": "success",
            "path": clip_path,
            "frames": frame_count,
            "total_detections": total_detections,
            "avg_count": avg_count,
            "max_count": max_count,
            "min_count": min_count if min_count != float('inf') else 0,
            "avg_fps": avg_fps
        }
        
        print(f"Frames: {frame_count}")
        print(f"Total detections: {total_detections}")
        print(f"Avg count: {avg_count:.2f}")
        print(f"Max count: {max_count}")
        print(f"Min count: {min_count if min_count != float('inf') else 0}")
        print(f"Avg FPS: {avg_fps:.1f}")
    
    # Save results
    import json
    output_path = Path("output") / "benchmark_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nBenchmark results saved to: {output_path}")
    
    return 0


def cmd_calibrate(args, config):
    """Run intensity calibration for a room."""
    calibrator = create_calibrator(config)
    config_path = Path(__file__).parent / "config.yaml"

    if args.status:
        print("=== Intensity Calibration Status ===\n")
        rooms = calibrator.get_all_rooms()
        if not rooms:
            print("No rooms configured. Run calibration first.")
            return 0

        for room_id, calib in rooms.items():
            is_day = calibrator.is_daytime()
            dark_th, medium_th = calib.get_thresholds(is_day)
            print(f"Room: {room_id}")
            print(f"  Last calibrated: {calib.last_calibrated or 'Never'}")
            print(f"  Sample count: {calib.sample_count}")
            print(f"  Day thresholds: dark={calib.day_dark_threshold}, medium={calib.day_medium_threshold}")
            print(f"  Night thresholds: dark={calib.night_dark_threshold}, medium={calib.night_medium_threshold}")

            warnings = calibrator.validate_thresholds(room_id)
            if warnings:
                print(f"  Warnings: {', '.join(warnings)}")
            print()
        return 0

    if args.update:
        room_id = args.room or "default"
        calibrator.update_thresholds(
            room_id=room_id,
            day_dark=args.day_dark,
            day_medium=args.day_medium,
            night_dark=args.night_dark,
            night_medium=args.night_medium
        )
        calibrator.save_to_config(config_path)
        print(f"Updated thresholds for room '{room_id}'")
        calib = calibrator.get_calibration(room_id)
        if calib:
            print(f"  Day: dark={calib.day_dark_threshold}, medium={calib.day_medium_threshold}")
            print(f"  Night: dark={calib.night_dark_threshold}, medium={calib.night_medium_threshold}")
        return 0

    if args.input:
        room_id = args.room or "default"
        print(f"Running auto-calibration for room '{room_id}'...")
        print(f"Input: {args.input}")

        extractor = VideoFrameExtractor(args.input)
        if not extractor.open():
            print(f"Error: Could not open video source: {args.input}")
            return 1

        sample_frames = config.get("intensity_calibration", {}).get("auto_calibrate", {}).get("sample_frames", 30)
        frames_to_sample = args.samples or sample_frames

        print(f"Collecting {frames_to_sample} frames...")
        frames = []
        frame_idx = 0

        while frame_idx < frames_to_sample:
            frame = extractor.read_frame()
            if frame is None:
                break
            frames.append(frame)
            frame_idx += 1

            if frame_idx % 10 == 0:
                print(f"  Collected {frame_idx}/{frames_to_sample} frames...")

        extractor.release()

        if len(frames) < 10:
            print(f"Error: Not enough frames collected ({len(frames)}). Need at least 10.")
            return 1

        sensitivity = args.sensitivity or config.get("intensity_calibration", {}).get("auto_calibrate", {}).get("sensitivity", 1.0)

        print("Running auto-calibration algorithm...")
        calib = calibrator.auto_calibrate(
            room_id=room_id,
            empty_frames=frames,
            occupied_frames=None,
            sensitivity=sensitivity
        )

        calibrator.save_to_config(config_path)

        print(f"\nCalibration complete for room '{room_id}'!")
        print(f"  Day thresholds: dark={calib.day_dark_threshold}, medium={calib.day_medium_threshold}")
        print(f"  Night thresholds: dark={calib.night_dark_threshold}, medium={calib.night_medium_threshold}")
        print(f"  Samples used: {calib.sample_count}")

        brightnesses = [calibrator.calculate_brightness(f) for f in frames[:10]]
        avg_brightness = sum(brightnesses) / len(brightnesses)
        print(f"  Average brightness (sample): {avg_brightness:.1f}")
        print(f"\nConfig saved to: {config_path}")
        return 0

    print("Use --input to run calibration, --status to view current settings, or --update to modify thresholds")
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="WattWatch - Intelligent Occupancy Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py detect video.mp4
  python main.py detect image.jpg --output result.jpg
  python main.py live
  python main.py benchmark
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # detect command
    detect_parser = subparsers.add_parser("detect", help="Run detection on video or image")
    detect_parser.add_argument("input", help="Input video or image path")
    detect_parser.add_argument("-o", "--output", help="Output path for annotated result")
    detect_parser.add_argument("--max-frames", type=int, help="Maximum frames to process")
    detect_parser.add_argument("--confidence", type=float, default=None, help="Detection confidence threshold (0-1)")
    detect_parser.set_defaults(func=cmd_detect)
    
    # live command
    live_parser = subparsers.add_parser("live", help="Run live detection on camera")
    live_parser.add_argument("-c", "--camera", default="0", help="Camera index or device")
    live_parser.set_defaults(func=cmd_live)
    
    # benchmark command
    benchmark_parser = subparsers.add_parser("benchmark", help="Run benchmark on test clips")
    benchmark_parser.set_defaults(func=cmd_benchmark)
    
    # calibrate command
    calibrate_parser = subparsers.add_parser("calibrate", help="Intensity calibration for rooms")
    calibrate_parser.add_argument("input", nargs="?", help="Input video for calibration (optional)")
    calibrate_parser.add_argument("-r", "--room", help="Room ID for calibration")
    calibrate_parser.add_argument("-s", "--samples", type=int, help="Number of frames to sample")
    calibrate_parser.add_argument("--sensitivity", type=float, help="Calibration sensitivity (0.5-1.5)")
    calibrate_parser.add_argument("--status", action="store_true", help="Show current calibration status")
    calibrate_parser.add_argument("--update", action="store_true", help="Update thresholds manually")
    calibrate_parser.add_argument("--day-dark", type=int, help="Day dark threshold (0-255)")
    calibrate_parser.add_argument("--day-medium", type=int, help="Day medium threshold (0-255)")
    calibrate_parser.add_argument("--night-dark", type=int, help="Night dark threshold (0-255)")
    calibrate_parser.add_argument("--night-medium", type=int, help="Night medium threshold (0-255)")
    calibrate_parser.set_defaults(func=cmd_calibrate)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 1
    
    # Load config
    config = load_config()
    
    # Run command
    return args.func(args, config)


if __name__ == "__main__":
    sys.exit(main())