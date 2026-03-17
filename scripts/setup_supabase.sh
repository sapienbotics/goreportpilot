#!/bin/bash
# Setup Supabase for ReportPilot
# Run this script once to initialize the database schema
# Prerequisites: Supabase CLI installed and logged in
#
# Usage:
#   chmod +x scripts/setup_supabase.sh
#   ./scripts/setup_supabase.sh

echo "ReportPilot — Supabase Setup"
echo "=============================="
echo "Run migrations via:"
echo "  supabase db push"
echo "Or paste supabase/migrations/001_initial_schema.sql into the Supabase Dashboard SQL editor."
