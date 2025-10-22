# Credit Approval System

[cite_start]This project is a backend credit approval system, built as part of the Alemeno Internship assignment[cite: 2]. It provides a set of RESTful APIs to manage customers, assess loan eligibility based on a custom credit score, and process new loans.

The entire application is containerized using Docker and uses Celery for asynchronous background tasks.

## Tech Stack

* [cite_start]**Backend:** Python, Django 4+ [cite: 7]
* [cite_start]**API:** Django Rest Framework [cite: 7]
* [cite_start]**Database:** PostgreSQL [cite: 12]
* **Background Tasks:** Celery
* **Message Broker:** Redis
* **Data Processing:** Pandas
* [cite_start]**Containerization:** Docker & Docker Compose [cite: 11]

## Features

* [cite_start]**Dockerized Environment:** All services (web, database, worker) run in isolated containers from a single command[cite: 93].
* [cite_start]**Background Data Ingestion:** Loads initial customer and loan data from `.xlsx` files using Celery background workers[cite: 35].
* [cite_start]**Customer Registration:** Register new customers with a dynamically calculated credit limit[cite: 39].
* **Loan Eligibility Check:** A complex eligibility check based on:
    * [cite_start]A custom credit score (analyzing past loan performance, activity, and volume) [cite: 48-57].
    * [cite_start]Interest rate slabs based on the score [cite: 59-63].
    * [cite_start]A check to ensure total EMIs do not exceed 50% of monthly salary[cite: 64].
* [cite_start]**Loan Processing:** API endpoints to create new loans, view specific loan details, and list all loans for a given customer[cite: 72, 79, 83].

## Setup and Installation

### Prerequisites

* **Docker**
* **Docker Compose** (Usually included with Docker Desktop)

### Running the Application

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
    cd your-repo-name
    ```

2.  **Add Data Files**
    * Create a `data/` directory in the project root.
    * [cite_start]Place your `customer_data.xlsx` [cite: 14] [cite_start]and `loan_data.xlsx` [cite: 23] files inside this `data/` folder.

3.  **Build and Run Containers**
    * Run the following command from the project's root directory:
    ```bash
    docker compose up --build
    ```
    * (Optional) To run in detached mode, use `docker compose up --build -d`.

The API server will be running at `http://localhost:8000/`.

## Data Ingestion

The initial customer and loan data must be loaded into the database using the Celery background task.

1.  **Open a Shell in the Web Container**
    * While the containers are running, open a **new terminal** and run:
    ```bash
    docker compose exec web python manage.py shell
    ```

2.  **Trigger the Tasks**
    * Inside the Django shell, import and run the tasks:
    ```python
    from api.tasks import ingest_customer_data, ingest_loan_data

    # This will queue the tasks to be run by the celery worker
    ingest_customer_data.delay()
    ingest_loan_data.delay()
    ```
    * You can monitor the logs of your `celery-worker` container to see the ingestion progress.

## API Endpoints

All endpoints are prefixed with `/api/`.

---

### 1. Register Customer

* [cite_start]**Endpoint:** `POST /api/register/` [cite: 38]
* **Description:** Adds a new customer to the system. [cite_start]The `approved_limit` is automatically calculated as `36 * monthly_salary` (rounded to the nearest lakh)[cite: 41].

[cite_start]**Request Body:** [cite: 43]

| Field          | Value                          |
| :------------- | :----------------------------- |
| `first_name`   | First Name of customer (string) |
| `last_name`    | Last Name of customer (string)  |
| `age`          | Age of customer (int)          |
| `monthly_income` | Monthly income of individual (int) |
| `phone_number` | Phone number (int)             |

[cite_start]**Response Body (201 Created):** [cite: 46]

| Field          | Value                          |
| :------------- | :----------------------------- |
| `customer_id`  | Id of customer (int)           |
| `name`         | Name of customer (string)      |
| `age`          | Age of customer (int)          |
| `monthly_income` | Monthly income of individual (int) |
| `approved_limit` | Approved credit limit (int)    |
| `phone_number` | Phone number (int)             |

---

### 2. Check Loan Eligibility

* [cite_start]**Endpoint:** `POST /api/check-eligibility/` [cite: 47]
* **Description:** Checks if a customer is eligible for a loan based on their credit score and financial health. [cite_start]It returns whether the loan can be approved and a corrected interest rate if the provided one is too low for the customer's risk profile [cite: 65-67].

[cite_start]**Request Body:** [cite: 69]

| Field         | Value                        |
| :------------ | :--------------------------- |
| `customer_id` | Id of customer (int)         |
| `loan_amount` | Requested loan amount (float) |
| `interest_rate` | Interest rate on loan (float) |
| `tenure`      | Tenure of loan (int)         |

[cite_start]**Response Body (200 OK):** [cite: 71]

| Field                   | Value                                                              |
| :---------------------- | :----------------------------------------------------------------- |
| `customer_id`           | Id of customer (int)                                               |
| `approval`              | Can loan be approved (bool)                                        |
| `interest_rate`         | Interest rate on loan (float)                                      |
| `corrected_interest_rate` | Corrected Interest Rate (float)                                    |
| `tenure`                | Tenure of loan (int)                                               |
| `monthly_installment`   | Monthly installment to be paid as repayment (float)                |

---

### 3. Create Loan

* [cite_start]**Endpoint:** `POST /api/create-loan/` [cite: 72]
* **Description:** Processes a new loan based on the eligibility check. If the loan is not approved, a message will be provided.

[cite_start]**Request Body:** [cite: 75]

| Field         | Value                        |
| :------------ | :--------------------------- |
| `customer_id` | Id of customer (int)         |
| `loan_amount` | Requested loan amount (float) |
| `interest_rate` | Interest rate on loan (float) |
| `tenure`      | Tenure of loan (int)         |

[cite_start]**Response Body (201 Created or 200 OK):** [cite: 78]

| Field               | Value                                                 |
| :------------------ | :---------------------------------------------------- |
| `loan_id`           | Id of approved loan, null otherwise (int)             |
| `customer_id`       | Id of customer (int)                                  |
| `loan_approved`     | Is the loan approved (bool)                           |
| `message`           | Appropriate message if loan is not approved (string) |
| `monthly_installment` | Monthly installment to be paid as repayment (float)   |

---

### 4. View Loan (by Loan ID)

* [cite_start]**Endpoint:** `GET /api/view-loan/<loan_id>/` [cite: 79]
* **Description:** View details of a specific loan, including nested customer information.

[cite_start]**Response Body (200 OK):** [cite: 82]

| Field               | Value                                                 |
| :------------------ | :---------------------------------------------------- |
| `loan_id`           | Id of approved loan (int)                             |
| `customer`          | JSON object of customer details (JSON)                |
| `loan_amount`       | Requested loan amount (float)                          |
| `interest_rate`     | Interest rate of the approved loan (float)            |
| `monthly_installment` | Monthly installment to be paid as repayment (float)   |
| `tenure`            | Tenure of loan (int)                                  |

---

### 5. View Loans (by Customer ID)

* [cite_start]**Endpoint:** `GET /api/view-loans/<customer_id>/` [cite: 83]
* **Description:** View all current loans for a specific customer.

[cite_start]**Response Body (200 OK):** A list of loan items. [cite: 85]

[cite_start]**Each loan item in the list:** [cite: 87]

| Field               | Value                                                 |
| :------------------ | :---------------------------------------------------- |
| `loan_id`           | Id of approved loan (int)                             |
| `loan_amount`       | Requested loan amount (float)                          |
| `interest_rate`     | Interest rate of the approved loan (float)            |
| `monthly_installment` | Monthly installment to be paid as repayment (float)   |
| `repayments_left`   | No of EMIs left (int)                                 |
