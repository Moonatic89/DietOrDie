import {
  User,
  UserProfile,
  HealthMetrics,
  DailyNutritionSummary,
  MealEntry,
  FoodItem,
  AIAnalyzeFoodResponse,
  RideSession,
  RideLogResult,
  UserJourneyProgress,
  Journey,
  WeightLog,
  BodyCompositionLog,
  BodyCompositionCreateInput,
  BodyCompositionBulkInput,
  AIProgressReview
} from './types';

const API_BASE = '/api';

export function getAuthToken(): string | null {
  return localStorage.getItem('dietordie_token');
}

export function setAuthToken(token: string) {
  localStorage.setItem('dietordie_token', token);
}

export function removeAuthToken() {
  localStorage.removeItem('dietordie_token');
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errMessage = 'Errore di connessione al server';
    try {
      const data = await response.json();
      errMessage = data.detail || data.message || errMessage;
    } catch {
      // fallback
    }
    throw new Error(errMessage);
  }

  return response.json();
}

// --- AUTH ---
export async function login(username: string, password: string):Promise<{ access_token: string; user_id: number; username: string; full_name?: string }> {
  const data = await request<{ access_token: string; user_id: number; username: string; full_name?: string }>('/auth/login-json', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  setAuthToken(data.access_token);
  return data;
}

export async function register(username: string, password: string, fullName?: string): Promise<{ access_token: string; user_id: number; username: string; full_name?: string }> {
  const data = await request<{ access_token: string; user_id: number; username: string; full_name?: string }>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, password, full_name: fullName }),
  });
  setAuthToken(data.access_token);
  return data;
}

export async function getMe(): Promise<User> {
  return request<User>('/auth/me');
}

export async function getUsersList(): Promise<Array<{ id: number; username: string; full_name?: string }>> {
  return request<Array<{ id: number; username: string; full_name?: string }>>('/auth/users-list');
}

// --- PROFILE ---
export async function updateProfile(profile: Partial<UserProfile>): Promise<UserProfile> {
  return request<UserProfile>('/profile', {
    method: 'PUT',
    body: JSON.stringify(profile),
  });
}

export async function getHealthMetrics(): Promise<HealthMetrics> {
  return request<HealthMetrics>('/profile/metrics');
}

export async function getWeightHistory(): Promise<WeightLog[]> {
  return request<WeightLog[]>('/profile/weight-history');
}

export async function addWeightLog(weight_kg: number, notes?: string): Promise<WeightLog> {
  return request<WeightLog>('/profile/weight-log', {
    method: 'POST',
    body: JSON.stringify({ weight_kg, notes }),
  });
}

// --- NUTRITION ---
export async function getDailySummary(dateStr: string): Promise<DailyNutritionSummary> {
  return request<DailyNutritionSummary>(`/nutrition/summary/${dateStr}`);
}

export async function createMeal(meal: {
  meal_type: string;
  date?: string;
  title: string;
  total_calories: number;
  total_protein: number;
  total_carbs: number;
  total_fat: number;
  notes?: string;
  image_path?: string;
  items?: FoodItem[];
}): Promise<MealEntry> {
  return request<MealEntry>('/nutrition/meals', {
    method: 'POST',
    body: JSON.stringify(meal),
  });
}

export async function deleteMeal(mealId: number): Promise<{ status: string }> {
  return request<{ status: string }>(`/nutrition/meals/${mealId}`, {
    method: 'DELETE',
  });
}

export async function analyzeFoodPhoto(file: File): Promise<AIAnalyzeFoodResponse> {
  const formData = new FormData();
  formData.append('file', file);
  return request<AIAnalyzeFoodResponse>('/nutrition/analyze-photo', {
    method: 'POST',
    body: formData,
  });
}

// --- RIDES & GAMIFICATION ---
export async function getRides(): Promise<RideSession[]> {
  return request<RideSession[]>('/rides');
}

export async function getActiveRide(): Promise<RideSession | null> {
  return request<RideSession | null>('/rides/active');
}


export async function logRide(ride: {
  duration_seconds: number;
  distance_km: number;
  avg_speed_kmh?: number;
  calories_burned?: number;
  resistance_level?: number;
  heart_rate_avg?: number;
  notes?: string;
  photo_path?: string;
  journey_id?: number;
}): Promise<RideLogResult> {
  return request<RideLogResult>('/rides', {
    method: 'POST',
    body: JSON.stringify(ride),
  });
}

export async function analyzeDisplayPhoto(file: File): Promise<{
  distance_km?: number;
  duration_seconds?: number;
  avg_speed_kmh?: number;
  calories_burned?: number;
  notes?: string;
  image_url?: string;
}> {
  const formData = new FormData();
  formData.append('file', file);
  return request('/rides/analyze-display', {
    method: 'POST',
    body: formData,
  });
}

export async function getJourneys(): Promise<Journey[]> {
  return request<Journey[]>('/journeys');
}

export async function getActiveJourney(): Promise<UserJourneyProgress> {
  return request<UserJourneyProgress>('/journeys/active');
}

export async function activateJourney(journeyId: number): Promise<UserJourneyProgress> {
  return request<UserJourneyProgress>(`/journeys/${journeyId}/activate`, {
    method: 'POST',
  });
}

// --- BIOIMPEDANCE BODY COMPOSITION ---
export async function getBodyCompositionLogs(): Promise<BodyCompositionLog[]> {
  return request<BodyCompositionLog[]>('/profile/body-composition');
}

export async function addBodyCompositionLog(data: BodyCompositionCreateInput): Promise<BodyCompositionLog> {
  return request<BodyCompositionLog>('/profile/body-composition', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function addBodyCompositionBulkJson(bulk: BodyCompositionBulkInput): Promise<BodyCompositionLog> {
  return request<BodyCompositionLog>('/profile/body-composition/bulk-json', {
    method: 'POST',
    body: JSON.stringify(bulk),
  });
}

export async function deleteBodyCompositionLog(id: number): Promise<void> {
  return request<void>(`/profile/body-composition/${id}`, {
    method: 'DELETE',
  });
}

export async function getBodyCompositionAiReview(): Promise<AIProgressReview> {
  return request<AIProgressReview>('/profile/body-composition/ai-review');
}

