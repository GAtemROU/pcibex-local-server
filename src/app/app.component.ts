
// app.component.ts
import { HeaderComponent } from './header/header.component';
import { FooterComponent } from './footer/footer.component';
import { LoginComponent } from './login/login.component';
import { Component, inject } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from './auth.service';
import { toSignal } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { ToastComponent } from './toast/toast.component';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
  imports: [
    HeaderComponent,  
    FooterComponent,
    RouterModule,
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    ToastComponent
  ]
})
export class AppComponent {
  private authService = inject(AuthService);
  public router = inject(Router);
  
  isAuthenticated = toSignal(this.authService.authState$);

  constructor() {
    // Redirect to landing page if already authenticated
    if (this.isAuthenticated()) {
      this.router.navigate(['/landing']);
    }
  }

  onLoginSuccess() {
    this.router.navigate(['/landing']);
  }
}