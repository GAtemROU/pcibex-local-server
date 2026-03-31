import { CommonModule,DOCUMENT } from '@angular/common';
import { FormsModule, FormBuilder, FormGroup, Validators, ReactiveFormsModule} from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { Component, Renderer2, Inject } from '@angular/core';
import { ToastService } from '../toast.service';
import { AuthService } from '../auth.service';
import { environment } from '../../environments/environment.development';
import { ApiService } from '../api.service';

@Component({
  standalone: true,
  selector: 'app-reset-password',
  imports: [CommonModule, FormsModule, ReactiveFormsModule, RouterModule],
  templateUrl: './reset-password.component.html',
  styleUrl: './reset-password.component.css'
})

export class ResetPasswordComponent {
  resetForm: FormGroup;
  submitted = false;
  passwordMismatch = false;
  passwordVisible = false;

  payload = {
      username: '',
      password: '', // Plain text password to be hashed server-side
    };

  togglePasswordVisibility(): void {
    this.passwordVisible = !this.passwordVisible;
  }

  constructor(private fb: FormBuilder,
    private authService: AuthService, 
    private router: Router,
    private apiService: ApiService,
    private toastService: ToastService) {
    this.resetForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      newPassword: ['', [Validators.required, Validators.minLength(8)]],
      confirmPassword: ['', [Validators.required]],
    });
  }

  get f() {
    return this.resetForm.controls;
  }

  // Validate the New Password based on the regex rules
  validatePassword(password: string): string {
    if (password.length < 8) {
      return 'Password must be at least 8 characters';
    }
    if (!/[A-Z]/.test(password)) {
      return 'Password must contain at least one uppercase letter';
    }
    if (!/[a-z]/.test(password)) {
      return 'Password must contain at least one lowercase letter';
    }
    if (!/\d/.test(password)) {
      return 'Password must contain at least one digit';
    }
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      return 'Password must contain at least one special character';
    }
    return 'Password is valid';
  }

  // Check if New Password and Confirm Password match
  validatePasswords(): boolean {
    const newPassword = this.resetForm.get('newPassword')?.value;
    const confirmPassword = this.resetForm.get('confirmPassword')?.value;
    
    if (newPassword && confirmPassword && newPassword !== confirmPassword) {
      this.passwordMismatch = true;
      return false;
    } else {
      this.passwordMismatch = false;
      return true;
    }
  }

  // Submit form
 async onSubmit(): Promise<void> {
    this.submitted = true;

    if (this.resetForm.invalid || !this.validatePasswords()) {
      this.toastService.showError('Please correct the errors in the form.');
      return;
    }

    const email = this.resetForm.value.email;
    const newPassword = this.resetForm.value.newPassword;

    // Call the password reset API using async/await
    await this.resetPassword(email, newPassword);
  }

  // Function to send password reset request using fetch with async/await
async resetPassword(email: string, newPassword: string): Promise<void> {
    const payload = {
      username: email,
      password: newPassword,
    };

    try {
      const data = await this.apiService.resetPassword(payload)
      if (data?.message) {
        this.toastService.showSuccess('Password reset successfully.');
        this.router.navigate(['/login']);
      } else {
        this.toastService.showError('Error during password reset');
      }
    } catch (error) {
      this.toastService.showError('Failed to reset password');
      console.error('Reset password error:', error);
    }
  }
 
}
