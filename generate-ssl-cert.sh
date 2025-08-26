#!/bin/bash

# Script to generate self-signed SSL certificates for HTTPS support
# For production use, replace with proper SSL certificates from a CA

echo "Generating self-signed SSL certificates for HTTPS..."

# Create certs directory if it doesn't exist
mkdir -p certs

# Generate private key
openssl genrsa -out certs/key.pem 2048

# Generate certificate signing request
openssl req -new -key certs/key.pem -out certs/cert.csr -subj "/C=US/ST=State/L=City/O=Organization/CN=192.155.107.226"

# Generate self-signed certificate (valid for 365 days)
openssl x509 -req -in certs/cert.csr -signkey certs/key.pem -out certs/cert.pem -days 365

# Clean up CSR file
rm certs/cert.csr

# Set appropriate permissions
chmod 600 certs/key.pem
chmod 644 certs/cert.pem

echo "SSL certificates generated successfully!"
echo "Private key: certs/key.pem"
echo "Certificate: certs/cert.pem"
echo ""
echo "⚠️  WARNING: These are self-signed certificates for development/testing only!"
echo "   For production use, obtain proper SSL certificates from a trusted CA."
echo ""
echo "To use HTTPS:"
echo "1. Run this script: ./generate-ssl-cert.sh"
echo "2. Update your mobile app to use HTTPS and port 8443"
echo "3. Accept the self-signed certificate warning in your app"

