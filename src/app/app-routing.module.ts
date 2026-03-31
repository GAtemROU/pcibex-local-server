// app-routing.module.ts
import { Routes, RouterModule } from '@angular/router';
import { LandingComponent } from './landing/landing.component';  // Make sure this component is standalone
import { LoginComponent } from './login/login.component';      // Also standalone if needed
import { ResetPasswordComponent } from './reset-password/reset-password.component';
import { authGuard } from './auth.guard';
import { UserManagementComponent } from './user-management/user-management.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'reset-password', component: ResetPasswordComponent },
  {
    path: 'dashboard',
    component: LandingComponent,
    canActivate: [authGuard]
  },
  {
    path: 'user-management',
    component: UserManagementComponent,
    canActivate: [authGuard]
  },
  {
    path: '#', redirectTo: 'dashboard'
  },
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: '**', redirectTo: 'login' }
];

export const AppRoutingModule = RouterModule.forRoot(routes);
