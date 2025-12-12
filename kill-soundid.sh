#!/bin/bash

echo "🔨 Permanently disabling SoundID Reference..."
echo ""

# Try to bootout the service
echo "1. Booting out the service..."
sudo launchctl bootout system/com.sonarworks.soundid.reference.systemwide.ipc_proxy 2>/dev/null

# Disable it permanently
echo "2. Disabling the service permanently..."
sudo launchctl disable system/com.sonarworks.soundid.reference.systemwide.ipc_proxy 2>/dev/null

# Remove the plist file so it never loads again
echo "3. Removing the launch daemon file..."
sudo rm /Library/LaunchDaemons/com.sonarworks.soundid.reference.systemwide.ipc_proxy.plist

# Kill any running processes
echo "4. Killing running processes..."
sudo killall "SonarworksASPProxy" 2>/dev/null

# Restart audio system
echo "5. Restarting Core Audio (your audio will briefly cut out)..."
sudo killall coreaudiod

echo ""
echo "✅ Done! SoundID Reference has been permanently disabled."
echo "   It will not start automatically anymore."
echo ""
echo "   If you see 'No such file or directory' errors, that's fine -"
echo "   it means those components were already removed."
echo ""
echo "   You may want to restart your Mac to ensure all changes take effect."















