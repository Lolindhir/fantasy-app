
function Get-Config {
    
    # League Settings
    $Global:LeagueYear = 2025
    $Global:SalaryRelevantTeamSize = 20
    $Global:LeagueID = "1257421353431080960"

    # RapidAPI-Key für Tank01
    $Global:RapidAPIKey = "cccff76c4bmsh01946acbc2d3c0bp141721jsn161bd86f4c69"
    $Global:RapidAPIKeyAlt1 = "1e10165385msh4175f82e3d08e84p19fd3ejsn82f1e01c01aa"
    $Global:RapidAPIKeyAlt2 = "3a3482fb66msh803287ddb5773dbp185f31jsnc6f1e236cd5e"

    # Point Settings
    $Global:WeightTotal = 0.5
    $Global:WeightGame = 0.5

    return @{
        LeagueYear = $Global:LeagueYear
        SalaryRelevantTeamSize = $Global:SalaryRelevantTeamSize
        LeagueID = $Global:LeagueID
        RapidAPIKey = $Global:RapidAPIKey
        RapidAPIKeyAlt1 = $Global:RapidAPIKeyAlt1
        RapidAPIKeyAlt2 = $Global:RapidAPIKeyAlt2
        WeightTotal = $Global:WeightTotal
        WeightGame = $Global:WeightGame
    }
    
}