#!/usr/bin/env bash
set -euo pipefail

cd frontend
npm ci
npm run build
cd ..

rm -rf public
mkdir -p public
cp -r frontend/dist/. public/
