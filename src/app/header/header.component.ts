import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { AuthService } from '../auth.service';
import { Router, RouterModule } from '@angular/router';

@Component({
  selector: 'app-header',
  imports: [CommonModule, RouterModule],
  templateUrl: './header.component.html',
  styleUrl: './header.component.css'
})

export class HeaderComponent {
  isAdmin = false;
  constructor(private authService: AuthService, private router: Router) {
    this.isAdmin = this.authService.getRole() === 'ADMIN'
  }

  logout() {
    this.authService.logout()
    this.router.navigate(['/login'])
  }
}
