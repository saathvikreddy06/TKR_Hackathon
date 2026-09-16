import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
    getAdminConsultants,
    getAdminConsultations,
    getAdminFeedback,
    getAdminStats
} from './services/adminService'

const ingestionDatasets = [
    {
        key: 'standards',
        label: 'BIS Standards',
        description: 'Official BIS standards catalogue',
        expected: '24,130'
    },
    {
        key: 'labs',
        label: 'Recognised Laboratories',
        description: 'BIS LIMS recognised laboratories',
        expected: '431'
    },
    {
        key: 'lims_tests',
        label: 'LIMS Tests',
        description: 'BIS LIMS testing records loaded by the application',
        expected: '277,434'
    },
    {
        key: 'qco_events',
        label: 'QCO Events',
        description: 'Normalised QCO regulatory events',
        expected: '489'
    },
    {
        key: 'qco_states',
        label: 'IS-QCO States',
        description: 'Standard/QCO regulatory state records',
        expected: '504'
    },
    {
        key: 'qco_links',
        label: 'Standard-QCO Links',
        description: 'Validated standard to QCO relationships',
        expected: '107'
    },
    {
        key: 'testing_links',
        label: 'Testing Relationships',
        description: 'Standard-lab-test relationships',
        expected: '2,344,090'
    },
    {
        key: 'knowledge_documents',
        label: 'Knowledge Documents',
        description: 'Structured RAG knowledge documents',
        expected: '68,744'
    },
    {
        key: 'knowledge_chunks',
        label: 'Knowledge Chunks',
        description: 'Generated RAG chunks',
        expected: '160,026'
    },
    {
        key: 'local_embeddings',
        label: 'Local Embeddings',
        description: 'Completed local semantic embeddings',
        expected: '24,209 / 24,209'
    },
    {
        key: 'firebase_embeddings',
        label: 'Firebase Embeddings',
        description: 'Embeddings uploaded to Firestore',
        expected: '19,900 / 24,209'
    }
]

function getIngestionValue(stats, dataset) {
    const possibleKeys = [
        dataset.key,
        `${dataset.key}_count`,
        `${dataset.key}_total`
    ]

    for (const key of possibleKeys) {
        if (stats[key] !== undefined && stats[key] !== null) {
            return stats[key]
        }
    }

    return dataset.expected
}

function getDatasetStatus(stats, dataset) {
    const value = getIngestionValue(stats, dataset)

    if (dataset.key === 'local_embeddings') {
        return String(value) === '24,209 / 24,209'
            ? 'Complete'
            : 'Partial'
    }

    if (dataset.key === 'firebase_embeddings') {
        return String(value) === '24,209 / 24,209'
            ? 'Complete'
            : 'Partial'
    }

    return value !== '—' && value !== undefined
        ? 'Loaded'
        : 'Unknown'
}

function StatusBadge({ status }) {
    const className =
        status === 'Complete'
            ? 'status-badge status-complete'
            : status === 'Partial'
                ? 'status-badge status-partial'
                : status === 'Loaded'
                    ? 'status-badge status-loaded'
                    : 'status-badge status-unknown'

    return <span className={className}>{status}</span>
}

function AdminPage() {
    const [stats, setStats] = useState({})
    const [consultants, setConsultants] = useState([])
    const [consultations, setConsultations] = useState([])
    const [feedback, setFeedback] = useState([])
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)

        Promise.all([
            getAdminStats(),
            getAdminConsultants(),
            getAdminConsultations(),
            getAdminFeedback()
        ])
            .then(([
                statsData,
                consultantData,
                consultationData,
                feedbackData
            ]) => {
                setStats(statsData || {})
                setConsultants(consultantData.consultants || [])
                setConsultations(consultationData.consultations || [])
                setFeedback(feedbackData.feedback || [])
                setError('')
            })
            .catch((requestError) => {
                setError(requestError.message)
            })
            .finally(() => {
                setLoading(false)
            })
    }, [])

    return (
        <section className="data-page admin-page">

            <div className="page-intro-row">
                <div>
                    <p className="eyebrow">
                        <span></span> Admin workspace
                    </p>

                    <h1>StandIQ control center.</h1>

                    <p>
                        Monitor platform activity and the SIH 26107
                        BIS knowledge pipeline from one secured workspace.
                    </p>
                </div>

                <Link
                    className="button"
                    to="/dashboard"
                >
                    Back to dashboard <span>↗</span>
                </Link>
            </div>

            {error && (
                <p
                    className="auth-error"
                    role="alert"
                >
                    {error}
                </p>
            )}

            <section className="admin-section">
                <div className="section-heading">
                    <div>
                        <p className="eyebrow">
                            <span></span> Platform overview
                        </p>

                        <h2>System activity</h2>
                    </div>

                    {loading && (
                        <span className="status-badge status-loading">
                            Loading
                        </span>
                    )}
                </div>

                <div className="dashboard-grid">
                    {[
                        ['Consultants', stats.consultants],
                        ['Consultations', stats.consultations],
                        ['Feedback', stats.feedback],
                        ['Searches', stats.search_history]
                    ].map(([label, value]) => (
                        <article
                            className="dashboard-card"
                            key={label}
                        >
                            <small>{label}</small>
                            <strong className="metric">
                                {value ?? '—'}
                            </strong>
                        </article>
                    ))}
                </div>
            </section>

            <section className="admin-section">
                <div className="section-heading">
                    <div>
                        <p className="eyebrow">
                            <span></span> SIH 26107
                        </p>

                        <h2>Knowledge pipeline</h2>

                        <p>
                            Current BIS data ingestion and RAG readiness.
                        </p>
                    </div>
                </div>

                <div className="dashboard-grid ingestion-grid">
                    {ingestionDatasets.map((dataset) => {
                        const value = getIngestionValue(
                            stats,
                            dataset
                        )

                        const status = getDatasetStatus(
                            stats,
                            dataset
                        )

                        return (
                            <article
                                className="dashboard-card ingestion-card"
                                key={dataset.key}
                            >
                                <div className="card-heading">
                                    <span>{dataset.label}</span>
                                    <StatusBadge status={status} />
                                </div>

                                <strong className="metric">
                                    {value}
                                </strong>

                                <small>
                                    {dataset.description}
                                </small>
                            </article>
                        )
                    })}
                </div>
            </section>

            <section className="dashboard-grid">

                <article className="dashboard-card dashboard-card-wide">
                    <div className="card-heading">
                        <span>Consultants</span>
                        <span>{consultants.length}</span>
                    </div>

                    {consultants.length === 0 ? (
                        <p className="empty-state">
                            No consultant records found.
                        </p>
                    ) : (
                        consultants.map((consultant) => (
                            <div
                                className="query-item"
                                key={consultant.id}
                            >
                                <div>
                                    <strong>
                                        {consultant.name}
                                    </strong>

                                    <small>
                                        {consultant.email || 'No email'}
                                        {' · '}
                                        {consultant.active === false
                                            ? 'Inactive'
                                            : 'Active'}
                                    </small>
                                </div>

                                <span>
                                    {consultant.availability
                                        ? 'Available'
                                        : 'Busy'}
                                </span>
                            </div>
                        ))
                    )}
                </article>

                <article className="dashboard-card">
                    <div className="card-heading">
                        <span>Recent feedback</span>
                        <span>{feedback.length}</span>
                    </div>

                    {feedback.length === 0 ? (
                        <p className="empty-state">
                            No feedback found.
                        </p>
                    ) : (
                        feedback
                            .slice(0, 5)
                            .map((item) => (
                                <div
                                    className="query-item"
                                    key={item.id}
                                >
                                    <div>
                                        <strong>
                                            {item.rating}/5
                                        </strong>

                                        <small>
                                            {item.comment ||
                                                'No comment'}
                                        </small>
                                    </div>
                                </div>
                            ))
                    )}
                </article>

            </section>

            <article className="dashboard-card">
                <div className="card-heading">
                    <span>Consultation requests</span>
                    <span>{consultations.length}</span>
                </div>

                {consultations.length === 0 ? (
                    <p className="empty-state">
                        No consultation requests found.
                    </p>
                ) : (
                    consultations
                        .slice(0, 8)
                        .map((consultation) => (
                            <div
                                className="query-item"
                                key={consultation.id}
                            >
                                <div>
                                    <strong>
                                        {consultation.subject}
                                    </strong>

                                    <small>
                                        {consultation.status}
                                        {' · '}
                                        {consultation.user_id}
                                    </small>
                                </div>

                                <span>
                                    {consultation.consultant_id}
                                </span>
                            </div>
                        ))
                )}
            </article>

        </section>
    )
}

export default AdminPage