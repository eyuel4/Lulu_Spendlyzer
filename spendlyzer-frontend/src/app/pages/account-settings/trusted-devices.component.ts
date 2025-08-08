import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TrustedDeviceService, TrustedDevice } from '../../services/trusted-device.service';
import { NotificationService } from '../../services/notification.service';

@Component({
  selector: 'app-trusted-devices',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700">
      <div class="px-6 py-4 border-b border-slate-200 dark:border-slate-700">
        <h3 class="text-lg font-semibold text-slate-900 dark:text-white">Trusted Devices</h3>
        <p class="text-sm text-slate-600 dark:text-slate-400 mt-1">
          Manage devices that can skip two-factor authentication for 7 days
        </p>
      </div>

      <div class="p-6">
        <div *ngIf="loading" class="flex justify-center py-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>

        <div *ngIf="!loading && devices.length === 0" class="text-center py-8">
          <div class="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg class="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
            </svg>
          </div>
          <h4 class="text-lg font-medium text-slate-900 dark:text-white mb-2">No Trusted Devices</h4>
          <p class="text-slate-600 dark:text-slate-400">
            You haven't trusted any devices yet. When you enable "Remember this device" during 2FA, it will appear here.
          </p>
        </div>

        <div *ngIf="!loading && devices.length > 0" class="space-y-4">
          <div class="flex justify-between items-center mb-4">
            <span class="text-sm text-slate-600 dark:text-slate-400">
              {{ devices.length }} device{{ devices.length !== 1 ? 's' : '' }}
            </span>
            <button
              (click)="revokeAllDevices()"
              [disabled]="revokingAll"
              class="text-sm text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span *ngIf="revokingAll">Revoking...</span>
              <span *ngIf="!revokingAll">Revoke All</span>
            </button>
          </div>

          <div *ngFor="let device of devices" class="border border-slate-200 dark:border-slate-700 rounded-lg p-4">
            <div class="flex items-start justify-between">
              <div class="flex-1">
                <div class="flex items-center space-x-3">
                  <div class="w-10 h-10 bg-indigo-100 dark:bg-indigo-900 rounded-lg flex items-center justify-center">
                    <svg class="w-5 h-5 text-indigo-600 dark:text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                    </svg>
                  </div>
                  <div>
                    <h4 class="font-medium text-slate-900 dark:text-white">{{ device.device_name }}</h4>
                    <p class="text-sm text-slate-600 dark:text-slate-400">{{ device.location }}</p>
                  </div>
                </div>
                
                <div class="mt-3 grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span class="text-slate-500 dark:text-slate-400">Last used:</span>
                    <span class="ml-1 text-slate-900 dark:text-white">{{ formatDate(device.last_used_at) }}</span>
                  </div>
                  <div>
                    <span class="text-slate-500 dark:text-slate-400">Expires:</span>
                    <span class="ml-1 text-slate-900 dark:text-white">{{ formatDate(device.expires_at) }}</span>
                  </div>
                </div>

                <div class="mt-2">
                  <span 
                    *ngIf="isDeviceExpired(device.expires_at)" 
                    class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                  >
                    Expired
                  </span>
                  <span 
                    *ngIf="!isDeviceExpired(device.expires_at)" 
                    class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                  >
                    {{ getDaysUntilExpiration(device.expires_at) }} days left
                  </span>
                </div>
              </div>

              <button
                (click)="revokeDevice(device.id)"
                [disabled]="revokingDevices.has(device.id)"
                class="ml-4 text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span *ngIf="revokingDevices.has(device.id)">Revoking...</span>
                <span *ngIf="!revokingDevices.has(device.id)">Revoke</span>
              </button>
            </div>
          </div>
        </div>

        <div *ngIf="error" class="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg">
          <p class="text-sm text-red-700 dark:text-red-300">{{ error }}</p>
        </div>
      </div>
    </div>
  `,
  styles: []
})
export class TrustedDevicesComponent implements OnInit {
  devices: TrustedDevice[] = [];
  loading = false;
  error = '';
  revokingAll = false;
  revokingDevices = new Set<number>();

  constructor(
    private trustedDeviceService: TrustedDeviceService,
    private notificationService: NotificationService
  ) {}

  ngOnInit(): void {
    this.loadDevices();
  }

  loadDevices(): void {
    this.loading = true;
    this.error = '';

    this.trustedDeviceService.getTrustedDevices().subscribe({
      next: (response) => {
        this.devices = response.devices;
        this.loading = false;
      },
      error: (error) => {
        this.error = 'Failed to load trusted devices';
        this.loading = false;
        console.error('Error loading trusted devices:', error);
      }
    });
  }

  revokeDevice(deviceId: number): void {
    this.revokingDevices.add(deviceId);

    this.trustedDeviceService.revokeTrustedDevice(deviceId).subscribe({
      next: () => {
        this.devices = this.devices.filter(device => device.id !== deviceId);
        this.revokingDevices.delete(deviceId);
        this.notificationService.addNotification({
          title: 'Device Revoked',
          message: 'Device revoked successfully',
          type: 'success',
          isRead: false
        });
      },
      error: (error) => {
        this.revokingDevices.delete(deviceId);
        this.notificationService.addNotification({
          title: 'Revoke Failed',
          message: 'Failed to revoke device',
          type: 'error',
          isRead: false
        });
        console.error('Error revoking device:', error);
      }
    });
  }

  revokeAllDevices(): void {
    if (!confirm('Are you sure you want to revoke all trusted devices? This will require 2FA on all devices.')) {
      return;
    }

    this.revokingAll = true;

    this.trustedDeviceService.revokeAllTrustedDevices().subscribe({
      next: (response) => {
        this.devices = [];
        this.revokingAll = false;
        this.notificationService.addNotification({
          title: 'Devices Revoked',
          message: `Revoked ${response.revoked_count} devices`,
          type: 'success',
          isRead: false
        });
      },
      error: (error) => {
        this.revokingAll = false;
        this.notificationService.addNotification({
          title: 'Revoke Failed',
          message: 'Failed to revoke all devices',
          type: 'error',
          isRead: false
        });
        console.error('Error revoking all devices:', error);
      }
    });
  }

  formatDate(dateString: string): string {
    return this.trustedDeviceService.formatDate(dateString);
  }

  isDeviceExpired(expiresAt: string): boolean {
    return this.trustedDeviceService.isDeviceExpired(expiresAt);
  }

  getDaysUntilExpiration(expiresAt: string): number {
    return this.trustedDeviceService.getDaysUntilExpiration(expiresAt);
  }
} 