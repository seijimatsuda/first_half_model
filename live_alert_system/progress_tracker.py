"""Progress tracking module for the live betting alert system."""

import time
import sys
from typing import Optional
from datetime import datetime, timedelta


class ProgressTracker:
    """Handles real-time progress tracking with time estimates and visual progress bars."""
    
    def __init__(self, total_steps: int, operation_name: str):
        """Initialize progress tracking with total steps and operation name."""
        self.total_steps = total_steps
        self.operation_name = operation_name
        self.current_step = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.estimated_remaining = 0
        self.progress_rate = 0
        self.current_operation = operation_name
        
        # Progress bar settings
        self.bar_width = 50
        self.update_interval = 0.1  # Minimum time between updates (seconds)
        
        print(f"\n🚀 Starting: {operation_name}")
        print(f"📊 Total steps: {total_steps}")
        print("-" * 60)
    
    def update(self, current_step: int, current_operation: str = None):
        """Update progress bar with current step and operation."""
        # Throttle updates to avoid terminal spam
        current_time = time.time()
        if current_time - self.last_update_time < self.update_interval and current_step < self.total_steps:
            return
        
        self.current_step = current_step
        if current_operation:
            self.current_operation = current_operation
        
        # Calculate progress metrics
        percentage = (current_step / self.total_steps) * 100 if self.total_steps > 0 else 0
        elapsed_time = current_time - self.start_time
        
        # Calculate progress rate and estimated remaining time
        if elapsed_time > 0 and current_step > 0:
            self.progress_rate = current_step / elapsed_time
            if self.progress_rate > 0:
                self.estimated_remaining = (self.total_steps - current_step) / self.progress_rate
            else:
                self.estimated_remaining = 0
        else:
            self.estimated_remaining = 0
        
        # Create visual progress bar
        filled_width = int((current_step / self.total_steps) * self.bar_width) if self.total_steps > 0 else 0
        bar = "█" * filled_width + "░" * (self.bar_width - filled_width)
        
        # Format time strings
        elapsed_str = self._format_time(elapsed_time)
        remaining_str = self._format_time(self.estimated_remaining)
        
        # Create progress line
        progress_line = f"{self.current_operation}... [{bar}] {percentage:.1f}% ({elapsed_str} elapsed, {remaining_str} remaining)"
        
        # Update display
        sys.stdout.write(f"\r{progress_line}")
        sys.stdout.flush()
        
        self.last_update_time = current_time
    
    def finish(self):
        """Mark operation as complete and display final statistics."""
        total_time = time.time() - self.start_time
        total_time_str = self._format_time(total_time)
        
        # Clear the progress line and show completion
        sys.stdout.write(f"\r{' ' * 100}\r")  # Clear line
        sys.stdout.flush()
        
        print(f"✅ Completed: {self.operation_name}")
        print(f"⏱️  Total time: {total_time_str}")
        print(f"📊 Final progress: {self.current_step}/{self.total_steps} steps")
        print("-" * 60)
    
    def _format_time(self, seconds: float) -> str:
        """Format time in MM:SS or HH:MM:SS format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = int(seconds % 60)
            return f"{minutes}m {remaining_seconds}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            remaining_seconds = int(seconds % 60)
            return f"{hours}h {minutes}m {remaining_seconds}s"
    
    def set_operation(self, operation_name: str):
        """Update the current operation name."""
        self.current_operation = operation_name
    
    def get_elapsed_time(self) -> float:
        """Get the total elapsed time in seconds."""
        return time.time() - self.start_time
    
    def get_estimated_remaining(self) -> float:
        """Get the estimated remaining time in seconds."""
        return self.estimated_remaining


class NestedProgressTracker:
    """Handles nested progress tracking for complex operations."""
    
    def __init__(self, total_operations: int, main_operation: str):
        """Initialize nested progress tracking."""
        self.total_operations = total_operations
        self.main_operation = main_operation
        self.current_operation = 0
        self.start_time = time.time()
        self.operation_trackers = {}
        
        print(f"\n🎯 Starting nested operation: {main_operation}")
        print(f"📊 Total operations: {total_operations}")
        print("=" * 60)
    
    def start_operation(self, operation_name: str, total_steps: int) -> ProgressTracker:
        """Start tracking a new operation."""
        self.current_operation += 1
        operation_tracker = ProgressTracker(total_steps, operation_name)
        self.operation_trackers[operation_name] = operation_tracker
        
        print(f"\n📋 Operation {self.current_operation}/{self.total_operations}: {operation_name}")
        return operation_tracker
    
    def finish_operation(self, operation_name: str):
        """Finish tracking an operation."""
        if operation_name in self.operation_trackers:
            self.operation_trackers[operation_name].finish()
    
    def finish_all(self):
        """Finish all operations and display summary."""
        total_time = time.time() - self.start_time
        total_time_str = self._format_time(total_time)
        
        print(f"\n🎉 All operations completed: {self.main_operation}")
        print(f"⏱️  Total time: {total_time_str}")
        print(f"📊 Operations completed: {self.current_operation}/{self.total_operations}")
        print("=" * 60)
    
    def _format_time(self, seconds: float) -> str:
        """Format time in MM:SS or HH:MM:SS format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = int(seconds % 60)
            return f"{minutes}m {remaining_seconds}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            remaining_seconds = int(seconds % 60)
            return f"{hours}h {minutes}m {remaining_seconds}s"


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_progress_tracker():
        """Test the progress tracker with sample operations."""
        
        # Test basic progress tracker
        print("Testing basic progress tracker...")
        tracker = ProgressTracker(100, "Sample Operation")
        
        for i in range(101):
            await asyncio.sleep(0.05)  # Simulate work
            tracker.update(i, f"Processing item {i}")
        
        tracker.finish()
        
        # Test nested progress tracker
        print("\nTesting nested progress tracker...")
        nested_tracker = NestedProgressTracker(3, "Complex Analysis")
        
        # Operation 1
        op1 = nested_tracker.start_operation("Data Collection", 50)
        for i in range(51):
            await asyncio.sleep(0.02)
            op1.update(i, f"Collecting data {i}")
        nested_tracker.finish_operation("Data Collection")
        
        # Operation 2
        op2 = nested_tracker.start_operation("Data Processing", 30)
        for i in range(31):
            await asyncio.sleep(0.03)
            op2.update(i, f"Processing data {i}")
        nested_tracker.finish_operation("Data Processing")
        
        # Operation 3
        op3 = nested_tracker.start_operation("Report Generation", 20)
        for i in range(21):
            await asyncio.sleep(0.04)
            op3.update(i, f"Generating report {i}")
        nested_tracker.finish_operation("Report Generation")
        
        nested_tracker.finish_all()
    
    # Run test
    asyncio.run(test_progress_tracker())
