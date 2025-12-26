import { Component, OnInit, AfterViewInit, ViewChild } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ThemeService } from './services/theme.service';
import { ModalService } from './services/modal.service';
import { ModalContainerComponent } from './components/modal-container/modal-container.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, ModalContainerComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent implements OnInit, AfterViewInit {
  title = 'spendlyzer-frontend';
  @ViewChild(ModalContainerComponent) modalContainer?: ModalContainerComponent;

  constructor(
    private themeService: ThemeService,
    private modalService: ModalService
  ) {}

  ngOnInit(): void {
    // Theme service will auto-initialize
  }

  ngAfterViewInit(): void {
    // Set view container ref for modal service
    if (this.modalContainer) {
      // The modal container will handle modal rendering
    }
  }
}
