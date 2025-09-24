#!/usr/bin/env python3
"""
Chat runner for the enhanced live betting alert system.
Run this to interact with the system through chat commands.
"""

import asyncio
import os
import sys
from chat_interface import ChatInterface


async def main():
    """Main chat interface loop."""
    print("🤖 ENHANCED LIVE BETTING ALERT SYSTEM - CHAT INTERFACE")
    print("=" * 60)
    print("Type 'help' for available commands or 'exit' to quit")
    print("=" * 60)
    
    interface = ChatInterface()
    
    while True:
        try:
            # Get user input
            command = input("\n💬 Enter command: ").strip()
            
            # Check for exit
            if command.lower() in ['exit', 'quit', 'bye']:
                print("👋 Goodbye!")
                break
            
            # Process command
            if command:
                print("🤖 Processing...")
                result = await interface.process_command(command)
                print(f"\n{result}")
            
        except KeyboardInterrupt:
            print("\n\n⏹️  Chat interrupted by user")
            print("👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    # Check if we're in the right directory
    if not os.path.exists("config.py"):
        print("❌ Error: config.py not found")
        print("💡 Please run this script from the live_alert_system directory")
        sys.exit(1)
    
    # Run the chat interface
    asyncio.run(main())
