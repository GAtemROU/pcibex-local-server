import { Component, ViewEncapsulation } from '@angular/core';
import { AuthService } from '../auth.service'; 
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms'; 
import { CommonModule } from '@angular/common'; 
import { ResetPasswordComponent } from '../reset-password/reset-password.component';
import { ToastService } from '../toast.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
  imports: [CommonModule, FormsModule, RouterModule],
})

export class LoginComponent {
  credentials = {
    username: '',
    password: '',
  };

  constructor(private authService: AuthService, private router: Router, private toastService: ToastService) {}

  goToResetPassword(): void {
    this.router.navigate(['/reset-password']);
  }

  async onSubmit() {
    try {
      let response = await this.authService.login(this.credentials);
      console.log(response)
      if(response.data) {
         if(response.data.token)
    {
      if(response.message) {
        this.goToResetPassword()
      }
      else {
        this.router.navigate(['/dashboard']);
      }
      
    }
    else {
      this.toastService.showError(response.error || 'Login failed. Please check your credentials.')
    }
      }
      else {
        this.toastService.showError('Login failed. Please check your credentials.')
      }
   
    } catch (error: any) {
      this.toastService.showError(error.error || 'Login failed. Please check your credentials.')
    }
  }
}
