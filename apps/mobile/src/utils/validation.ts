import { z } from 'zod';

// Mirrors services/api/app/schemas/auth.py
export const loginSchema = z.object({
  email: z.string().trim().toLowerCase().email('Invalid email').max(320),
  password: z.string().min(1).max(256),
});
export type LoginInput = z.infer<typeof loginSchema>;

export const registerSchema = z.object({
  email: z.string().trim().toLowerCase().email('Invalid email').max(320),
  password: z.string().min(8, 'At least 8 characters').max(256),
  display_name: z.string().min(1).max(255),
  avatar_url: z.string().max(2048).optional().or(z.literal('')),
});
export type RegisterInput = z.infer<typeof registerSchema>;

// Mirrors services/api/app/schemas/mission.py MissionCreate
export const missionCreateSchema = z.object({
  title: z.string().min(1).max(200),
  description: z.string().max(2000).optional().or(z.literal('')),
  location: z.object({
    lat: z.number().min(-90).max(90),
    lng: z.number().min(-180).max(180),
  }),
  search_radius_m: z.number().int().min(100).max(50_000).default(3000),
});
export type MissionCreateInput = z.infer<typeof missionCreateSchema>;

// Mirrors services/api/app/schemas/preference.py PreferencePayload
export const preferenceSchema = z.object({
  budget_max_cents: z.number().int().min(0).nullable().optional(),
  distance_tolerance_m: z.number().int().min(0).nullable().optional(),
  cuisines_like: z.array(z.string()).optional(),
  cuisines_dislike: z.array(z.string()).optional(),
  dietary_restrictions: z.array(z.string()).optional(),
  vibe: z.string().max(255).nullable().optional(),
  noise_tolerance: z.number().int().min(0).max(5).nullable().optional(),
  seating_preference: z.string().max(32).nullable().optional(),
  urgency: z.number().int().min(0).max(5).nullable().optional(),
  hunger_level: z.number().int().min(0).max(5).nullable().optional(),
  raw_comment: z.string().max(4000).nullable().optional(),
});
export type PreferenceInput = z.infer<typeof preferenceSchema>;
