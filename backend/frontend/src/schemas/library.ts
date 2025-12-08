/**
 * Zod schemas for library API runtime validation
 */

import { z } from 'zod';

export const LibraryItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  created_at: z.string(), // ISO timestamp
  duration_sec: z.number().optional(),
  voice: z.enum(['Swara', 'Diya']).optional(),
  template: z.string().optional(),
  state: z.string().optional(),
  thumbnail_url: z.string().optional(),
  video_url: z.string().optional(),
  error: z.string().optional(),
});

export const FetchLibraryResponseSchema = z.object({
  entries: z.array(LibraryItemSchema),
  total: z.number(),
  page: z.number(),
  pageSize: z.number(),
});

export type LibraryItem = z.infer<typeof LibraryItemSchema>;
export type FetchLibraryResponse = z.infer<typeof FetchLibraryResponseSchema>;
