
#!/bin/bash

# Stop on error
set -e

# Paths
PROJECT_DIR="<path to your project root>"
DIST_DIR="$PROJECT_DIR/dist"
TARGET_DIR="/var/www/vd-pcibex"
USER="pcibex" (or your deployment user)
GROUP="pcibex" (or your deployment usergroup)

echo "Starting build..."

# Step 1: Build project
cd $PROJECT_DIR
sudo npm run build

echo "Build completed."

# Step 2: Remove old deployment
echo "Cleaning old files..."
sudo rm -rf $TARGET_DIR/*

# Step 3: Copy new dist files
echo "Copying dist to vd-pcibex..."
sudo cp -r $DIST_DIR/* $TARGET_DIR/

# Step 4: Change ownership
echo "Setting ownership to pcibex..."
sudo chown -R $USER:$GROUP $TARGET_DIR

# Step 5: Set permissions
echo "Setting permissions..."
sudo find $TARGET_DIR -type d -exec chmod 755 {} \;
sudo find $TARGET_DIR -type f -exec chmod 644 {} \;

echo "Restarting NGINX"
sudo systemctl restart nginx

echo "Deployment completed successfully."


