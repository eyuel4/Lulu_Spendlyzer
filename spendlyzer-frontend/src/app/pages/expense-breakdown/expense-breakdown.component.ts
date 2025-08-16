import { Component, Input, ViewChild, ElementRef, AfterViewInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Chart, ChartConfiguration, DoughnutController, ArcElement, Tooltip, Legend } from 'chart.js';

export interface CategoryData {
  category: string;
  amount: number;
  percentage: number;
  icon: string;
  color: string;
}

@Component({
  selector: 'app-expense-breakdown',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './expense-breakdown.component.html',
  styleUrls: ['./expense-breakdown.component.scss']
})
export class ExpenseBreakdownComponent implements AfterViewInit, OnChanges {
  @Input() categoryData: CategoryData[] = [];
  @Input() currentTheme: 'light' | 'dark' = 'light';
  
  @ViewChild('expenseChart', { static: false }) chartCanvas!: ElementRef<HTMLCanvasElement>;
  private chart: Chart | null = null;

  ngAfterViewInit(): void {
    // Register Chart.js components
    Chart.register(DoughnutController, ArcElement, Tooltip, Legend);
    this.createOrUpdateChart();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['categoryData'] || changes['currentTheme']) {
      setTimeout(() => {
        this.createOrUpdateChart();
      }, 100);
    }
  }

  private createOrUpdateChart(): void {
    if (!this.chartCanvas?.nativeElement) return;

    if (this.chart) {
      this.chart.destroy();
    }

    const ctx = this.chartCanvas.nativeElement.getContext('2d');
    if (!ctx) return;

    const isDark = this.currentTheme === 'dark';
    const textColor = isDark ? '#E5E7EB' : '#374151';

    const config: ChartConfiguration = {
      type: 'doughnut',
      data: {
        labels: this.categoryData.map(d => `${d.icon} ${d.category}`),
        datasets: [{
          data: this.categoryData.map(d => d.amount),
          backgroundColor: this.categoryData.map(d => d.color),
          borderColor: isDark ? '#374151' : '#FFFFFF',
          borderWidth: 2,
          hoverBorderWidth: 3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom' as const,
            labels: {
              color: textColor,
              font: {
                size: 12
              },
              usePointStyle: true,
              pointStyle: 'circle'
            }
          },
          tooltip: {
            backgroundColor: isDark ? '#1F2937' : '#FFFFFF',
            titleColor: textColor,
            bodyColor: textColor,
            borderColor: isDark ? '#374151' : '#E5E7EB',
            borderWidth: 1,
            callbacks: {
              label: (context) => {
                const data = this.categoryData[context.dataIndex];
                return `${data.category}: $${data.amount.toFixed(2)} (${data.percentage.toFixed(1)}%)`;
              }
            }
          }
        }
      }
    };

    this.chart = new Chart(ctx, config);
  }
}
