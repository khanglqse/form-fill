import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/router'
import axios from 'axios'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart
} from 'recharts'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

const COLORS = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe', '#43e97b', '#fa709a', '#fee140', '#30cfd0', '#330867']

export default function Dashboard() {
  const router = useRouter()
  const [overview, setOverview] = useState<any>(null)
  const [timeseries, setTimeseries] = useState<any>(null)
  const [deviceInsights, setDeviceInsights] = useState<any>(null)
  const [dropoffInsights, setDropoffInsights] = useState<any>(null)
  const [hourlyInsights, setHourlyInsights] = useState<any>(null)
  const [jobStats, setJobStats] = useState<any>(null)
  const [jobLogs, setJobLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [overviewRes, timeseriesRes, deviceRes, dropoffRes, hourlyRes, jobStatsRes, jobLogsRes] = await Promise.all([
        axios.get(`${API_BASE}/gold/overview`),
        axios.get(`${API_BASE}/gold/timeseries?days=7`),
        axios.get(`${API_BASE}/gold/insights/device`),
        axios.get(`${API_BASE}/gold/insights/dropoff`),
        axios.get(`${API_BASE}/gold/insights/hourly`),
        axios.get(`${API_BASE}/jobs/stats/summary`).catch((err) => {
          console.error('Error loading job stats:', err)
          return { data: null }
        }),
        axios.get(`${API_BASE}/jobs?limit=20`).catch((err) => {
          console.error('Error loading job logs:', err)
          return { data: { jobs: [] } }
        })
      ])
      setOverview(overviewRes.data)
      setTimeseries(timeseriesRes.data)
      setDeviceInsights(deviceRes.data)
      setDropoffInsights(dropoffRes.data)
      setHourlyInsights(hourlyRes.data)
      if (jobStatsRes?.data) {
        setJobStats(jobStatsRes.data)
        console.log('Job stats loaded:', jobStatsRes.data)
      }
      if (jobLogsRes?.data?.jobs) {
        setJobLogs(jobLogsRes.data.jobs)
        console.log('Job logs loaded:', jobLogsRes.data.jobs.length, 'jobs')
      }
    } catch (error) {
      console.error('Error loading dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await axios.post(`${API_BASE}/gold/refresh`)
      await loadData()
    } catch (error) {
      console.error('Error refreshing data:', error)
    } finally {
      setRefreshing(false)
    }
  }

  const styles = {
    container: {
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '2rem',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    },
    card: {
      maxWidth: '1400px',
      margin: '0 auto',
      background: 'white',
      borderRadius: '24px',
      boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
      overflow: 'hidden',
    },
    header: {
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      color: 'white',
      padding: '2rem',
      display: 'flex',
      justifyContent: 'space-between' as const,
      alignItems: 'center' as const,
    },
    title: {
      fontSize: '2rem',
      fontWeight: 'bold',
      margin: 0,
    },
    button: {
      background: 'rgba(255,255,255,0.2)',
      border: 'none',
      color: 'white',
      borderRadius: '12px',
      padding: '0.75rem 1.5rem',
      cursor: 'pointer',
      fontSize: '1rem',
      fontWeight: '500',
      transition: 'all 0.2s',
    },
    content: {
      padding: '2rem',
    },
    statsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: '1.5rem',
      marginBottom: '2rem',
    },
    statCard: {
      background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
      borderRadius: '16px',
      padding: '1.5rem',
      textAlign: 'center' as const,
    },
    statValue: {
      fontSize: '2rem',
      fontWeight: 'bold',
      color: '#667eea',
      margin: '0.5rem 0',
    },
    statLabel: {
      fontSize: '0.9rem',
      color: '#666',
      textTransform: 'uppercase' as const,
      letterSpacing: '1px',
    },
    chartContainer: {
      marginBottom: '2rem',
      padding: '1.5rem',
      background: '#f8f9fa',
      borderRadius: '16px',
    },
    chartsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(2, 1fr)',
      gap: '2rem',
      marginBottom: '2rem',
    },
    chartTitle: {
      fontSize: '1.3rem',
      fontWeight: '600',
      marginBottom: '1rem',
      color: '#333',
    },
    loading: {
      textAlign: 'center' as const,
      padding: '3rem',
      color: '#666',
      fontSize: '1.1rem',
    },
    table: {
      width: '100%',
      borderCollapse: 'collapse' as const,
      marginTop: '1rem',
    },
    tableHeader: {
      background: '#667eea',
      color: 'white',
      padding: '1rem',
      textAlign: 'left' as const,
      fontWeight: '600',
    },
    tableRow: {
      borderBottom: '1px solid #e9ecef',
    },
    tableCell: {
      padding: '1rem',
      color: '#333',
    },
  }

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <div style={styles.loading}>Đang tải dữ liệu dashboard...</div>
        </div>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      <style jsx>{`
        @media (max-width: 1024px) {
          .charts-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
      <div style={styles.card}>
        <div style={styles.header}>
          <h1 style={styles.title}>📊 Gold Layer Dashboard</h1>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button
              style={styles.button}
              onClick={() => router.push('/')}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.3)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.2)'
              }}
            >
              ← Về trang chủ
            </button>
            <button
              style={styles.button}
              onClick={handleRefresh}
              disabled={refreshing}
              onMouseEnter={(e) => {
                if (!refreshing) {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.3)'
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.2)'
              }}
            >
              {refreshing ? '⏳ Đang làm mới...' : '🔄 Làm mới dữ liệu'}
            </button>
          </div>
        </div>

        <div style={styles.content}>
          {/* Overall Statistics */}
          {overview?.overall && (
            <div style={styles.statsGrid}>
              <div style={styles.statCard}>
                <div style={styles.statLabel}>Tổng số biểu mẫu</div>
                <div style={styles.statValue}>{overview.overall.total_forms}</div>
              </div>
              <div style={styles.statCard}>
                <div style={styles.statLabel}>Tổng số phiên</div>
                <div style={styles.statValue}>{overview.overall.total_sessions}</div>
              </div>
              <div style={styles.statCard}>
                <div style={styles.statLabel}>Phiên hoàn thành</div>
                <div style={styles.statValue}>{overview.overall.total_completed_sessions}</div>
              </div>
              <div style={styles.statCard}>
                <div style={styles.statLabel}>Tỷ lệ hoàn thành</div>
                <div style={styles.statValue}>{overview.overall.overall_completion_rate}%</div>
              </div>
            </div>
          )}

          {/* Charts Grid - 2 columns */}
          <div className="charts-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '2rem', marginBottom: '2rem' }}>
            {/* Time Series Chart */}
            {timeseries?.daily_sessions && timeseries.daily_sessions.length > 0 && (
              <div style={styles.chartContainer}>
                <h2 style={styles.chartTitle}>📈 Xu hướng phiên theo thời gian (7 ngày)</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={timeseries.daily_sessions}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="sessions" stroke="#667eea" strokeWidth={2} name="Số phiên" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Top Forms Chart */}
            {overview?.top_forms && overview.top_forms.length > 0 && (
              <div style={styles.chartContainer}>
                <h2 style={styles.chartTitle}>🏆 Top 10 biểu mẫu phổ biến</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={overview.top_forms.slice(0, 10)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="form_title" angle={-45} textAnchor="end" height={100} />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="statistics.total_sessions" fill="#667eea" name="Tổng phiên" />
                    <Bar dataKey="statistics.completed_sessions" fill="#764ba2" name="Phiên hoàn thành" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Forms Table - Compact */}
          {overview?.top_forms && overview.top_forms.length > 0 && (
            <div style={styles.chartContainer}>
              <h2 style={styles.chartTitle}>📊 Top biểu mẫu</h2>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.tableHeader}>Biểu mẫu</th>
                    <th style={styles.tableHeader}>Tổng phiên</th>
                    <th style={styles.tableHeader}>Hoàn thành</th>
                    <th style={styles.tableHeader}>Tỷ lệ (%)</th>
                  </tr>
                </thead>
                <tbody>
                  {overview.top_forms.slice(0, 10).map((form: any, idx: number) => (
                    <tr key={idx} style={styles.tableRow}>
                      <td style={styles.tableCell}>
                        <a
                          href={`/forms/${encodeURIComponent(form.form_id)}`}
                          style={{ color: '#667eea', textDecoration: 'none' }}
                        >
                          {form.form_title}
                        </a>
                      </td>
                      <td style={styles.tableCell}>{form.statistics.total_sessions}</td>
                      <td style={styles.tableCell}>{form.statistics.completed_sessions}</td>
                      <td style={styles.tableCell}>{form.statistics.completion_rate}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Device Analysis & Job Stats - 2 columns */}
          <div className="charts-grid" style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(2, 1fr)', 
            gap: '2rem', 
            marginBottom: '2rem'
          } as React.CSSProperties}>
            {/* Device Analysis Section - Compact */}
            {deviceInsights?.devices && deviceInsights.devices.length > 0 && (
              <div style={styles.chartContainer}>
                <h2 style={styles.chartTitle}>📱 Phân tích theo thiết bị</h2>
                <div style={styles.statsGrid}>
                  {deviceInsights.devices.map((device: any, idx: number) => (
                    <div key={idx} style={styles.statCard}>
                      <div style={styles.statLabel}>{device.device_type.toUpperCase()}</div>
                      <div style={styles.statValue}>{device.completion_rate}%</div>
                      <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.5rem' }}>
                        {device.sessions} phiên
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Job Statistics Cards */}
            {jobStats?.overall && (
              <div style={styles.chartContainer}>
                <h2 style={styles.chartTitle}>📋 Job Statistics</h2>
                <div style={styles.statsGrid}>
                  <div style={styles.statCard}>
                    <div style={styles.statLabel}>Tổng số jobs</div>
                    <div style={styles.statValue}>{jobStats.overall.total_jobs}</div>
                  </div>
                  <div style={styles.statCard}>
                    <div style={styles.statLabel}>Thành công</div>
                    <div style={{ ...styles.statValue, color: '#43e97b' }}>{jobStats.overall.success}</div>
                  </div>
                  <div style={styles.statCard}>
                    <div style={styles.statLabel}>Thất bại</div>
                    <div style={{ ...styles.statValue, color: '#fa709a' }}>{jobStats.overall.failed}</div>
                  </div>
                  <div style={styles.statCard}>
                    <div style={styles.statLabel}>Đang chạy</div>
                    <div style={{ ...styles.statValue, color: '#667eea' }}>{jobStats.overall.running}</div>
                  </div>
                  <div style={styles.statCard}>
                    <div style={styles.statLabel}>Tỷ lệ thành công</div>
                    <div style={{ ...styles.statValue, color: '#43e97b' }}>{jobStats.overall.success_rate}%</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Job Logs Section - Compact */}
          {jobStats && (
            <div style={styles.chartContainer}>
              <h2 style={styles.chartTitle}>📋 Job Logs & Statistics</h2>
              
              {/* Job Type Summary Table */}
              {jobStats.by_type && jobStats.by_type.length > 0 && (
                <div style={{ marginBottom: '2rem' }}>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#667eea' }}>Phân bố theo loại job</h3>
                  <table style={styles.table}>
                    <thead>
                      <tr>
                        <th style={styles.tableHeader}>Loại job</th>
                        <th style={styles.tableHeader}>Tổng số</th>
                        <th style={styles.tableHeader}>Thành công</th>
                        <th style={styles.tableHeader}>Thất bại</th>
                        <th style={styles.tableHeader}>Đang chạy</th>
                        <th style={styles.tableHeader}>Thời gian TB (s)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {jobStats.by_type.map((jobType: any, idx: number) => {
                        const successStatus = jobType.statuses?.find((s: any) => s.status === 'success');
                        const failedStatus = jobType.statuses?.find((s: any) => s.status === 'failed');
                        const runningStatus = jobType.statuses?.find((s: any) => s.status === 'running');
                        return (
                          <tr key={idx} style={styles.tableRow}>
                            <td style={styles.tableCell}>
                              <span style={{
                                padding: '0.25rem 0.5rem',
                                borderRadius: '4px',
                                background: jobType.job_type === 'worker' ? '#e3f2fd' : '#f3e5f5',
                                color: jobType.job_type === 'worker' ? '#1976d2' : '#7b1fa2',
                                fontSize: '0.85rem',
                                fontWeight: '500'
                              }}>
                                {jobType.job_type}
                              </span>
                            </td>
                            <td style={styles.tableCell}>{jobType.total}</td>
                            <td style={{ ...styles.tableCell, color: '#43e97b' }}>{successStatus?.count || 0}</td>
                            <td style={{ ...styles.tableCell, color: '#fa709a' }}>{failedStatus?.count || 0}</td>
                            <td style={{ ...styles.tableCell, color: '#667eea' }}>{runningStatus?.count || 0}</td>
                            <td style={styles.tableCell}>
                              {successStatus?.avg_duration ? successStatus.avg_duration.toFixed(2) : '-'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Recent Job Logs Table */}
              {jobLogs && jobLogs.length > 0 && (
                <div>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#667eea' }}>Job Logs gần đây (Worker & Crawler)</h3>
                  <table style={styles.table}>
                    <thead>
                      <tr>
                        <th style={styles.tableHeader}>Job ID</th>
                        <th style={styles.tableHeader}>Loại</th>
                        <th style={styles.tableHeader}>Trạng thái</th>
                        <th style={styles.tableHeader}>Thời gian</th>
                        <th style={styles.tableHeader}>Thông tin</th>
                      </tr>
                    </thead>
                    <tbody>
                      {jobLogs.slice(0, 15).map((job: any, idx: number) => (
                        <tr key={idx} style={styles.tableRow}>
                          <td style={styles.tableCell}>
                            <div style={{ fontFamily: 'monospace', fontSize: '0.8rem', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {job.job_id}
                            </div>
                          </td>
                          <td style={styles.tableCell}>
                            <span style={{
                              padding: '0.25rem 0.5rem',
                              borderRadius: '4px',
                              background: job.job_type === 'worker' ? '#e3f2fd' : '#f3e5f5',
                              color: job.job_type === 'worker' ? '#1976d2' : '#7b1fa2',
                              fontSize: '0.85rem',
                              fontWeight: '500'
                            }}>
                              {job.job_type}
                            </span>
                          </td>
                          <td style={styles.tableCell}>
                            <span style={{
                              padding: '0.25rem 0.5rem',
                              borderRadius: '4px',
                              background: job.status === 'success' ? '#e8f5e9' : job.status === 'failed' ? '#ffebee' : '#e3f2fd',
                              color: job.status === 'success' ? '#2e7d32' : job.status === 'failed' ? '#c62828' : '#1976d2',
                              fontSize: '0.85rem',
                              fontWeight: '500'
                            }}>
                              {job.status === 'success' ? '✅ Thành công' : job.status === 'failed' ? '❌ Thất bại' : '⏳ Đang chạy'}
                            </span>
                          </td>
                          <td style={styles.tableCell}>
                            {job.duration_seconds ? (
                              <div>
                                <div style={{ fontSize: '0.9rem', fontWeight: '500' }}>{job.duration_seconds.toFixed(2)}s</div>
                                {job.start_time_iso && (
                                  <div style={{ fontSize: '0.75rem', color: '#666' }}>
                                    {new Date(job.start_time_iso).toLocaleString('vi-VN')}
                                  </div>
                                )}
                              </div>
                            ) : (
                              <div style={{ fontSize: '0.85rem', color: '#666' }}>
                                {job.start_time_iso ? new Date(job.start_time_iso).toLocaleString('vi-VN') : '-'}
                              </div>
                            )}
                          </td>
                          <td style={styles.tableCell}>
                            {job.metadata && (
                              <div style={{ fontSize: '0.8rem' }}>
                                {job.metadata.bucket && (
                                  <div><strong>Bucket:</strong> {job.metadata.bucket}</div>
                                )}
                                {job.metadata.key && (
                                  <div><strong>Key:</strong> {job.metadata.key}</div>
                                )}
                                {job.metadata.form_id && (
                                  <div><strong>Form:</strong> {job.metadata.form_id}</div>
                                )}
                                {job.metadata.source_url && (
                                  <div><strong>Source:</strong> {job.metadata.source_url.substring(0, 40)}...</div>
                                )}
                                {job.error && (
                                  <div style={{ color: '#c62828', marginTop: '0.25rem' }}>
                                    <strong>Error:</strong> {job.error.substring(0, 60)}...
                                  </div>
                                )}
                              </div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

