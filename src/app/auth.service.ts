// auth.service.ts
import { Injectable, inject, Inject, signal, PLATFORM_ID } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, tap } from 'rxjs';
import { isPlatformBrowser } from '@angular/common';
import { environment } from '../environments/environment';
import { ApiService } from './api.service';


interface LoginCredentials {
  username: string;
  password: string;
}

@Injectable({
  providedIn: 'root',
})
export class AuthService {


  private http = inject(HttpClient);
  private isBrowser: boolean;

  private authStateSubject = new BehaviorSubject<boolean>(false);
  authState$ = this.authStateSubject.asObservable();

   public isAuthenticated = signal<boolean>(false);

  constructor(@Inject(PLATFORM_ID) private platformId: object, private apiService: ApiService) {
    this.isBrowser = isPlatformBrowser(this.platformId);
  }

  checkAuth () {
    const isAuthenticated = this.hasValidToken();
    this.authStateSubject.next(isAuthenticated);
    this.isAuthenticated.set(isAuthenticated);
    return this.isAuthenticated()
  }

  hasValidToken() {
    const token = this.getToken()
    const expiry = this.getTokenExpiry()
    let isTokenValid = false
    if(expiry) {
      isTokenValid = token !== null && expiry > Date.now();
      this.isAuthenticated.set(isTokenValid);
      this.authStateSubject.next(isTokenValid)
    }
    return isTokenValid;
  }

  getUserId () {
    if(this.isBrowser) {
      return sessionStorage.getItem('user_id')
    }
    return null
  }

  async login(credentials: LoginCredentials) {
   try {
     let response: any = await this.apiService.login(credentials)
    if (response.data.token && this.isBrowser) {
          sessionStorage.setItem('auth_token', response.data.token);
          sessionStorage.setItem('auth_token_expiry', (Date.now() + 3600000).toString()); // 1 hour expiry
          sessionStorage.setItem('username', response.data.user.username);
          sessionStorage.setItem('role', response.data.user.role);
          sessionStorage.setItem('full_name', response.data.user.full_name);
          sessionStorage.setItem('user_id', response.data.user._id || "")

          this.authStateSubject.next(true);
          this.isAuthenticated.set(true);
    }
    return response
   } catch (error) {
    console.log(error)
   }
  }

  logout() {
    if (this.isBrowser) {
      sessionStorage.removeItem('auth_token');
      sessionStorage.removeItem('auth_token_expiry');
      sessionStorage.removeItem('username');
      sessionStorage.removeItem('role');
      sessionStorage.removeItem('full_name');
      sessionStorage.removeItem('reset');
    }

    this.authStateSubject.next(false);
    this.isAuthenticated.set(false);
  }

  getRole () {
    if(this.isBrowser) {
      return sessionStorage.getItem('role') || null
    }
    return null
  }

  getTokenExpiry() {
    if(this.isBrowser) {
      return parseInt(sessionStorage.getItem('auth_token_expiry') || '0', 10)
    }
    return null;
  }

  getToken(): string | null {
    return this.isBrowser ? sessionStorage.getItem('auth_token') : null;
  }
}
