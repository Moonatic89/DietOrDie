export interface UserProfile {
  id: number;
  user_id: number;
  birth_date?: string;
  gender: string;
  height_cm?: number;
  current_weight_kg?: number;
  target_weight_kg?: number;
  activity_level: string;
  daily_calorie_target: number;
  notes?: string;
  updated_at?: string;
}

export interface HealthMetrics {
  bmi?: number;
  bmi_category?: string;
  bmr?: number;
  tdee?: number;
  recommended_calories?: number;
  weight_diff_kg?: number;
}

export interface User {
  id: number;
  username: string;
  email?: string;
  full_name?: string;
  avatar_url?: string;
  created_at: string;
  profile?: UserProfile;
  metrics?: HealthMetrics;
}

export interface WeightLog {
  id: number;
  weight_kg: number;
  recorded_at: string;
  notes?: string;
  created_at: string;
}

export interface FoodItem {
  id?: number;
  name: string;
  portion_g?: number;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
}

export interface MealEntry {
  id: number;
  meal_type: string; // colazione, pranzo, cena, spuntino
  date: string;
  title: string;
  total_calories: number;
  total_protein: number;
  total_carbs: number;
  total_fat: number;
  image_path?: string;
  notes?: string;
  created_at: string;
  items: FoodItem[];
}

export interface DailyNutritionSummary {
  date: string;
  target_calories: number;
  consumed_calories: number;
  burned_calories: number;
  net_calories: number;
  total_protein: number;
  total_carbs: number;
  total_fat: number;
  meals: MealEntry[];
}

export interface AIAnalyzeFoodResponse {
  dish_name: string;
  estimated_calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  confidence_notes: string;
  suggested_items: FoodItem[];
  image_url?: string;
}

export interface RideSession {
  id: number;
  user_id: number;
  journey_id?: number;
  session_uid?: string;
  duration_seconds: number;
  distance_km: number;
  avg_speed_kmh: number;
  current_speed_kmh?: number;
  rpm?: number;
  total_pedal_strokes?: number;
  telemetry_history_json?: string;
  calories_burned: number;
  resistance_level?: number;
  heart_rate_avg?: number;
  photo_path?: string;
  notes?: string;
  created_at: string;
  updated_at?: string;
}

export interface TelemetryPoint {
  sec: number;
  speed: number;
  rpm: number;
  km: number;
  watts: number;
}

export interface RideSplit {
  km: number;
  duration_seconds: number;
  avg_speed_kmh: number;
  avg_rpm: number;
  avg_watts: number;
}

export interface IntensityZones {
  zone1_recovery_sec: number;
  zone2_aerobic_sec: number;
  zone3_threshold_sec: number;
  zone1_pct: number;
  zone2_pct: number;
  zone3_pct: number;
}

export interface RidePerformanceData {
  ride_id: number;
  duration_seconds: number;
  distance_km: number;
  avg_speed_kmh: number;
  max_speed_kmh: number;
  avg_rpm: number;
  max_rpm: number;
  total_pedal_strokes: number;
  calories_burned: number;
  avg_watts: number;
  max_watts: number;
  resistance_level: number;
  zones: IntensityZones;
  splits: RideSplit[];
  telemetry_points: TelemetryPoint[];
}


export interface JourneyMilestone {
  id: number;
  order_index: number;
  name: string;
  distance_km: number;
  estimated_calories?: number;
  description?: string;
  lore_text?: string;
  image_url?: string;
  badge_icon: string;
  is_unlocked: boolean;
}

export interface Journey {
  id: number;
  slug: string;
  title: string;
  description?: string;
  universe: string;
  total_distance_km: number;
  estimated_calories_total?: number;
  cover_image?: string;
  badge_icon: string;
  milestones: JourneyMilestone[];
}

export interface UserJourneyProgress {
  id: number;
  journey: Journey;
  cumulative_distance_km: number;
  remaining_distance_km: number;
  progress_percentage: number;
  estimated_calories_total?: number;
  estimated_calories_remaining?: number;
  is_active: boolean;
  is_completed: boolean;
  current_milestone?: JourneyMilestone;
  next_milestone?: JourneyMilestone;
  distance_to_next_km?: number;
  unlocked_milestones_count: number;
  total_milestones_count: number;
}

export interface MilestoneUnlockCelebration {
  milestone_name: string;
  distance_km: number;
  lore_text?: string;
  badge_icon: string;
  journey_title: string;
}

export interface RideLogResult {
  ride: RideSession;
  progress?: UserJourneyProgress;
  newly_unlocked_milestone?: MilestoneUnlockCelebration;
}

export interface BodyCompositionDelta {
  days?: number;
  weight_kg?: number;
  bmi?: number;
  body_fat_pct?: number;
  subcutaneous_fat_pct?: number;
  visceral_fat?: number;
  muscle_mass_kg?: number;
  skeletal_muscle_pct?: number;
  bone_mass_kg?: number;
  fat_free_mass_kg?: number;
  body_water_pct?: number;
  protein_pct?: number;
}

export interface BodyCompositionLog {
  id: number;
  user_id: number;
  recorded_at: string;
  weight_kg: number;
  bmi?: number;
  body_fat_pct?: number;
  subcutaneous_fat_pct?: number;
  visceral_fat?: number;
  muscle_mass_kg?: number;
  skeletal_muscle_pct?: number;
  bone_mass_kg?: number;
  fat_free_mass_kg?: number;
  metabolic_age?: number;
  bmr_kcal?: number;
  body_water_pct?: number;
  protein_pct?: number;
  notes?: string;
  created_at: string;
  delta?: BodyCompositionDelta;
}

export interface BodyCompositionCreateInput {
  recorded_at?: string;
  weight_kg: number;
  bmi?: number;
  body_fat_pct?: number;
  subcutaneous_fat_pct?: number;
  visceral_fat?: number;
  muscle_mass_kg?: number;
  skeletal_muscle_pct?: number;
  bone_mass_kg?: number;
  fat_free_mass_kg?: number;
  metabolic_age?: number;
  bmr_kcal?: number;
  body_water_pct?: number;
  protein_pct?: number;
  notes?: string;
}

export interface BodyCompositionBulkInput {
  recorded_at?: string;
  raw_json?: string;
  data?: Record<string, any>;
}

export interface AIProgressReview {
  review_markdown: string;
  overall_trend: string;
  key_metrics_summary?: Record<string, any>;
  recommendations: string[];
}

