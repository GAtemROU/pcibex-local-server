import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';
import { CreateUserComponent } from '../create-user/create-user.component';
import { ApiService } from '../api.service';
import {environment} from '../../environments/environment.development';
import { ToastService } from '../toast.service';

@Component({
  selector: 'app-user-management',
  templateUrl: './user-management.component.html',
  styleUrls: ['./user-management.component.css'],
  imports: [CommonModule, RouterModule, CreateUserComponent]
})

export class UserManagementComponent {
  users: any = []
  constructor(private apiService: ApiService, private toastService: ToastService) {}

  ngOnInit() {
    this.loadUsers();
  }

  showOverlay = false;
  toggleOverlay() {
    this.showOverlay = !this.showOverlay;
  }

  closeOverlay() {
    this.showOverlay = false;
    this.ngOnInit();
  }

  async loadUsers(): Promise<void> {
  try {
    const items  = await this.apiService.getUsers();
    this.users = items;
    if(this.users.length === 0) {
      // No users
      this.toastService.showInfo('No users found');
    }

    for (const user of this.users) {
       const roleKey = user.role as keyof typeof environment.appRoles;
       user.role = environment.appRoles[roleKey] || user.role
       if(user.createdOn) {
          user.active_from = new Date(user.createdOn).toLocaleString(undefined,{ 
            month: 'long', 
            year: 'numeric' 
        });
      }
    }
  } catch (error) {
    console.error('Failed to load experiments:', error);
  }
}
}
