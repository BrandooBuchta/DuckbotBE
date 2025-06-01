#!/bin/bash

echo "⬇️  Stahuji ffmpeg..."
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
tar -xf ffmpeg-release-amd64-static.tar.xz
mv ffmpeg-*-amd64-static ffmpeg-bin
rm ffmpeg-release-amd64-static.tar.xz

echo "✅ ffmpeg připraven v ./ffmpeg-bin/"
