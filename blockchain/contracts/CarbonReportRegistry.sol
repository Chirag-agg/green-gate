// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title CarbonReportRegistry
 * @dev Stores and verifies CBAM carbon compliance reports on-chain.
 *      Used by GreenGate to provide immutable, trustless verification
 *      for EU importers receiving goods from Indian MSMEs.
 */
contract CarbonReportRegistry is Ownable {
    struct CarbonReport {
        bytes32 reportHash;
        address submitter;
        uint256 timestamp;
        string reportId;
        string companyName;
        uint256 co2Tonnes; // CO2 in kg (actual * 1000 for precision)
        bool isValid;
    }

    mapping(string => CarbonReport) public reports; // reportId => report
    mapping(bytes32 => string) public hashToReportId; // hash => reportId
    string[] public allReportIds;

    event ReportSubmitted(
        string reportId,
        bytes32 reportHash,
        address submitter,
        uint256 timestamp
    );

    event ReportRevoked(string reportId);

    constructor() Ownable(msg.sender) {}

    /**
     * @dev Submit a new carbon report to the registry.
     * @param reportId Unique report identifier (e.g., "GG-2026-00001")
     * @param reportHash SHA-256 hash of the full report JSON
     * @param companyName Name of the MSME company
     * @param co2Tonnes Total CO2 in kg (multiply actual tonnes by 1000)
     */
    function submitReport(
        string calldata reportId,
        bytes32 reportHash,
        string calldata companyName,
        uint256 co2Tonnes
    ) external onlyOwner {
        require(
            reports[reportId].timestamp == 0,
            "Report ID already exists"
        );
        require(
            bytes(hashToReportId[reportHash]).length == 0,
            "Report hash already registered"
        );

        CarbonReport memory report = CarbonReport({
            reportHash: reportHash,
            submitter: msg.sender,
            timestamp: block.timestamp,
            reportId: reportId,
            companyName: companyName,
            co2Tonnes: co2Tonnes,
            isValid: true
        });

        reports[reportId] = report;
        hashToReportId[reportHash] = reportId;
        allReportIds.push(reportId);

        emit ReportSubmitted(reportId, reportHash, msg.sender, block.timestamp);
    }

    /**
     * @dev Verify a report by its hash. Public/external — anyone can call.
     * @param reportHash The SHA-256 hash to verify
     * @return isValid Whether the report is valid
     * @return reportId The associated report ID
     * @return timestamp When the report was submitted
     */
    function verifyReport(
        bytes32 reportHash
    )
        external
        view
        returns (bool isValid, string memory reportId, uint256 timestamp)
    {
        string memory rid = hashToReportId[reportHash];
        if (bytes(rid).length == 0) {
            return (false, "", 0);
        }
        CarbonReport memory report = reports[rid];
        return (report.isValid, report.reportId, report.timestamp);
    }

    /**
     * @dev Get a full report by its ID.
     * @param reportId The report ID to look up
     * @return The full CarbonReport struct
     */
    function getReport(
        string calldata reportId
    ) external view returns (CarbonReport memory) {
        require(
            reports[reportId].timestamp != 0,
            "Report does not exist"
        );
        return reports[reportId];
    }

    /**
     * @dev Revoke a report. Only callable by the contract owner.
     * @param reportId The report ID to revoke
     */
    function revokeReport(string calldata reportId) external onlyOwner {
        require(
            reports[reportId].timestamp != 0,
            "Report does not exist"
        );
        require(reports[reportId].isValid, "Report already revoked");
        reports[reportId].isValid = false;
        emit ReportRevoked(reportId);
    }

    /**
     * @dev Get all report IDs ever submitted.
     * @return Array of all report ID strings
     */
    function getAllReportIds() external view returns (string[] memory) {
        return allReportIds;
    }
}
