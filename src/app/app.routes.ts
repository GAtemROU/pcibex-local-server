import { Routes, RouterModule } from '@angular/router';
import { LandingComponent } from './landing/landing.component';  // Make sure this component is standalone
import { LoginComponent } from './login/login.component';      // Also standalone if needed
import { ResetPasswordComponent } from './reset-password/reset-password.component';

export const routes: Routes = [
  { path: 'landing', component: LandingComponent },
  { path: 'reset-password', component: ResetPasswordComponent },
  { path: '', component: LoginComponent },  // Default route
  { path: '**', redirectTo: '' }            // Wildcard route for undefined paths
];