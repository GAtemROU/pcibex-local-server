// auth.guard.ts
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from './auth.service';

export const authGuard =() => {
  const authService = inject(AuthService);
  const router = inject(Router);
  let auth = authService.checkAuth() 
  if (auth) {
    return true;
  }
  
  // Redirect to login
  return router.parseUrl('/login');
};