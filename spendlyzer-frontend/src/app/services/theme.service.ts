import { Injectable, Renderer2, RendererFactory2, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { BehaviorSubject, Observable } from 'rxjs';

export type Theme = 'light' | 'dark';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private currentThemeSubject = new BehaviorSubject<Theme>('light');
  public currentTheme$ = this.currentThemeSubject.asObservable();
  
  private renderer: Renderer2;
  private isBrowser: boolean;

  constructor(
    rendererFactory: RendererFactory2,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {
    this.renderer = rendererFactory.createRenderer(null, null);
    this.isBrowser = isPlatformBrowser(this.platformId);
    
    if (this.isBrowser) {
      this.initializeTheme();
    }
  }

  private initializeTheme(): void {
    if (!this.isBrowser) return;
    
    try {
      // Check localStorage for saved theme preference
      let savedTheme: Theme | null = null;
      if (typeof window !== 'undefined' && window.localStorage) {
        savedTheme = localStorage.getItem('theme') as Theme;
      }
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      
      // Use saved theme, or system preference, or default to light
      const theme = savedTheme || (prefersDark ? 'dark' : 'light');
      this.setTheme(theme);
    } catch (error) {
      console.warn('Error initializing theme:', error);
      this.setTheme('light');
    }
  }

  getCurrentTheme(): Theme {
    return this.currentThemeSubject.value;
  }

  setTheme(theme: Theme): void {
    this.currentThemeSubject.next(theme);
    
    if (this.isBrowser) {
      try {
        if (typeof window !== 'undefined' && window.localStorage) {
          localStorage.setItem('theme', theme);
        }
      } catch (error) {
        console.warn('Error saving theme to localStorage:', error);
      }
      
      // Apply theme to document
      if (theme === 'dark') {
        this.renderer.addClass(document.documentElement, 'dark');
      } else {
        this.renderer.removeClass(document.documentElement, 'dark');
      }
    }
  }

  toggleTheme(): void {
    const currentTheme = this.getCurrentTheme();
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    this.setTheme(newTheme);
  }

  isDarkMode(): boolean {
    return this.getCurrentTheme() === 'dark';
  }
} 