export interface UserProfile {
  id: number;
  firstName: string;
  lastName: string;
  email: string;
  username: string;
  authProvider?: string; // 'local' or 'google'
  avatarUrl?: string;    // Google profile picture
} 