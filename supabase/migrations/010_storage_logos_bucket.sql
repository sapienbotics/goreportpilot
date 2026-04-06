-- ============================================================================
-- Migration 010: Supabase Storage — logos bucket
-- ============================================================================
-- Moves logo storage from Railway's ephemeral filesystem to Supabase Storage.
-- Logos need to be publicly readable (report generation downloads them by URL)
-- but only writeable by the owning user.
--
-- IMPORTANT: Run this in the Supabase SQL Editor.
-- After running, also create the bucket in the Supabase Dashboard:
--   Storage → New bucket → Name: "logos" → Public: ON → Create
-- (The bucket must exist before the policies take effect.)
-- ============================================================================

-- Allow authenticated users to upload to their own folder
-- Folder structure: logos/{user_id}/agency/logo.png
--                   logos/{user_id}/clients/{client_id}/logo.png
CREATE POLICY "Users can upload logos" ON storage.objects
  FOR INSERT TO authenticated
  WITH CHECK (
    bucket_id = 'logos'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );

-- Allow authenticated users to update/overwrite their own logos
CREATE POLICY "Users can update own logos" ON storage.objects
  FOR UPDATE TO authenticated
  USING (
    bucket_id = 'logos'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );

-- Allow authenticated users to delete their own logos
CREATE POLICY "Users can delete own logos" ON storage.objects
  FOR DELETE TO authenticated
  USING (
    bucket_id = 'logos'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );

-- Allow public read access to all logos (needed for report generation)
CREATE POLICY "Public read access for logos" ON storage.objects
  FOR SELECT TO public
  USING (bucket_id = 'logos');
